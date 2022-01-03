import os
from PIL import Image
import base45
import zlib
import cbor2
import flynn
from pyzbar.pyzbar import decode
from datetime import date, datetime, time, timedelta, timezone
from cose.messages import CoseMessage
from cryptography import x509
from cose.keys import EC2Key
import cose.headers
import requests
from werkzeug.datastructures import FileStorage
from pdf2image import convert_from_bytes
import json

from twogplus import (
    app,
)  # Source: https://github.com/ehn-dcc-development/ehn-dcc-schema/blob/release/1.3.0/valuesets/disease-agent-targeted.json

COVID_19_ID = "840539006"


def calc_vaccinated_till(data) -> date:
    hcert = data[-260][1]["v"][0]
    vaccination_date = date.fromisoformat(hcert["dt"])
    valid_until = None

    # Check if it is the last dosis
    if hcert["dn"] != hcert["sd"]:
        raise Exception("With this certificate you are not fully immunized.")

    # Check if it is johnson then its only 270 days or till first of 2022
    if hcert["sd"] == 1:
        valid_until = min(
            vaccination_date + timedelta(days=270),
            date(2022, 1, 3),
        )

    # Otherwise it is 270 days
    else:
        valid_until = vaccination_date + timedelta(days=270)

    if valid_until < date.today():
        raise Exception("This certificate is already expired.")

    return valid_until


def fetch_austria_data(ressource: str):
    # Check if the cache is still hot
    cache_filename = os.path.join(app.instance_path, f"{ressource}.cache")
    try:
        with open(cache_filename, "rb") as f:
            cache_time = os.path.getmtime(f)
            if (time.time() - cache_time) / 3600 > 12:
                raise Exception()

            return cbor2.loads(f.read())
    except Exception:
        pass

    # Not in cache so lets download it
    r = requests.get(f"https://dgc-trust.qr.gv.at/{ressource}")
    if r.status_code != 200:
        raise Exception("Unable to reach austria public key gateway")
    content = r.content

    # Update the cache
    with open(cache_filename, "wb") as f:
        f.write(content)

    return cbor2.loads(content)


# This code is adapted from the following repository:
# https://github.com/lazka/pygraz-covid-cert
def assert_cert_sign(cose_data: bytes):
    cose_msg = CoseMessage.decode(cose_data)
    required_kid = cose_msg.get_attr(cose.headers.KID)

    trustlist = fetch_austria_data("trustlist")
    for entry in trustlist["c"]:
        kid = entry["i"]
        cert = entry["c"]
        if kid == required_kid:
            break
    else:
        raise Exception(
            f"Unable validate certificate signature: kid '{required_kid}' not found"
        )
    found_cert = cert

    NOW = datetime.now(timezone.utc)
    cert = x509.load_der_x509_certificate(found_cert)
    if NOW < cert.not_valid_before.replace(tzinfo=timezone.utc):
        raise Exception("cert not valid")
    if NOW > cert.not_valid_after.replace(tzinfo=timezone.utc):
        raise Exception("cert not valid")

    # Convert the CERT to a COSE key and verify the signature
    # WARNING: we assume ES256 here but all other algorithms are allowed too
    assert cose_msg.get_attr(cose.headers.Algorithm).fullname == "ES256"
    public_key = cert.public_key()
    x = public_key.public_numbers().x.to_bytes(32, "big")
    y = public_key.public_numbers().y.to_bytes(32, "big")
    cose_key = EC2Key(crv="P_256", x=x, y=y)
    cose_msg.key = cose_key
    if not cose_msg.verify_signature():
        raise Exception("Unable to validate certificate signature")
    print("Validated certificate :)")


def verify_vaccinated_cert(file: FileStorage) -> str:
    # if the file is a pdf convert it to an image
    if file.filename.rsplit(".", 1)[1].lower() == "pdf":
        img = convert_from_bytes(file.read())[0]
    else:
        img = Image.open(file)

    # decode the qr code
    result = decode(img)
    if result == []:
        raise Exception("No QR Code was detected in the image")

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # TODO: I think cbor2 is a more modern library than flynn
    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # Verify that this is a vaccine certificate
    if "v" not in data[-260][1]:
        message = "The certificate must be for a vaccination."
        raise Exception(message)

    # Verify the data now
    if COVID_19_ID != data[-260][1]["v"][0]["tg"]:
        raise Exception("The certificate must be for covid19")

    # Verify the certificate signature
    assert_cert_sign(cose_data)

    # Verify the expiration date is ok for the event
    event_date = date.fromisoformat(app.config["EVENT_DATE"])
    if calc_vaccinated_till(data) < event_date:
        raise Exception(
            f"Your vaccine will expire before the event at {event_date}"
        )

    # Return the name from the certificate
    return data[-260][1]["nam"]["gnt"] + " " + data[-260][1]["nam"]["fnt"]


def verify_test_cert(file: FileStorage) -> str:
    # if the file is a pdf convert it to an image
    if file.filename.rsplit(".", 1)[1].lower() == "pdf":
        img = convert_from_bytes(file.read())[0]
    else:
        img = Image.open(file)

    # decode the qr code
    result = decode(img)
    if result == []:
        raise Exception("No QR Code was detected in the image")

    # decode base45
    data_zlib = base45.b45decode(result[0].data[4:])

    # decompress zlib
    cose_data = zlib.decompress(data_zlib)

    # TODO: I think cbor2 is a more modern library than flynn
    # decode cose
    cbor_data = flynn.decoder.loads(cose_data)[1][2]

    # decode cbor
    data = flynn.decoder.loads(cbor_data)

    # Verify that this is a test certificate
    if "t" not in data[-260][1]:
        message = "The certificate must be for a test"
        raise Exception(message)

    # Verify the data now
    if COVID_19_ID != data[-260][1]["t"][0]["tg"]:
        raise Exception("The test must be for covid19")
    # Verify that test was negative
    if "260415000" != data[-260][1]["t"][0]["tr"]:
        id = data[-260][1]["t"][0]["tr"]
        raise Exception(f"The test was not negative ({id})")
    # Verify a pcr test
    if "nm" not in data[-260][1]["t"][0]:
        raise Exception("We only allow PCR tests.")

    # Verify the certificate signature
    assert_cert_sign(cose_data)

    # Verify the expiration date is ok for the event
    event_date = datetime.fromisoformat(app.config["EVENT_DATE"])
    event_date += timedelta(hours=(24 + 6))
    time_of_test = datetime.fromisoformat(data[-260][1]["t"][0]["sc"][:-1])
    if time_of_test + timedelta(hours=48) < event_date:
        raise Exception(
            f"Your test will expire before the event at {event_date}\n"
            f"Time of test: {time_of_test}\nValid until: {time_of_test + timedelta(hours=48)}"
        )

    # Return the name from the certificate
    return data[-260][1]["nam"]["gnt"] + " " + data[-260][1]["nam"]["fnt"]
