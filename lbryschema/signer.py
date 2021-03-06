import ecdsa
import hashlib
from lbryschema.base import base_decode
from lbryschema.encoding import decode_b64_fields
from lbryschema.schema.certificate import Certificate
from lbryschema.schema.claim import Claim
from lbryschema.validator import validate_claim_id
from lbryschema.schema import V_0_0_1, CLAIM_TYPE, CLAIM_TYPES, CERTIFICATE_TYPE, VERSION
from lbryschema.schema import NIST256p, NIST384p, SECP256k1, SHA256, SHA384


class NIST_ECDSASigner(object):
    CURVE = None
    CURVE_NAME = None
    HASHFUNC = hashlib.sha256
    HASHFUNC_NAME = SHA256

    def __init__(self, private_key):
        self._private_key = private_key

    @property
    def private_key(self):
        return self._private_key

    @property
    def public_key(self):
        return self.private_key.get_verifying_key()

    @property
    def certificate(self):
        certificate_claim = {
            VERSION: V_0_0_1,
            CLAIM_TYPE: CERTIFICATE_TYPE,
            CLAIM_TYPES[CERTIFICATE_TYPE]: Certificate.load_from_key_obj(self.public_key,
                                                                         self.CURVE_NAME)
        }
        return Claim.load(certificate_claim)

    @classmethod
    def load_pem(cls, pem_string):
        return cls(ecdsa.SigningKey.from_pem(pem_string, hashfunc=cls.HASHFUNC_NAME))

    @classmethod
    def generate(cls):
        return cls(ecdsa.SigningKey.generate(curve=cls.CURVE, hashfunc=cls.HASHFUNC_NAME))

    def sign_stream_claim(self, claim, claim_address, cert_claim_id):
        validate_claim_id(cert_claim_id)
        if not base_decode(claim_address, 58):
            raise Exception("Invalid claim address")

        to_sign = "%s%s%s" % (base_decode(claim_address, 58),
                              claim.serialized_no_signature,
                              cert_claim_id.decode('hex'))

        digest = self.HASHFUNC(to_sign).digest()

        if not isinstance(self.private_key, ecdsa.SigningKey):
            raise Exception("Not given a signing key")
        sig_dict = {
            "version": V_0_0_1,
            "signatureType": self.CURVE_NAME,
            "signature": self.private_key.sign_digest_deterministic(digest, hashfunc=self.HASHFUNC),
            "certificateId": cert_claim_id.decode('hex')
        }

        msg = {
            "version": V_0_0_1,
            "stream": decode_b64_fields(claim.protobuf_dict)['stream'],
            "publisherSignature": sig_dict
        }

        return Claim.load(msg)


class NIST256pSigner(NIST_ECDSASigner):
    CURVE = ecdsa.NIST256p
    CURVE_NAME = NIST256p


class NIST384pSigner(NIST_ECDSASigner):
    CURVE = ecdsa.NIST384p
    CURVE_NAME = NIST384p
    HASHFUNC = hashlib.sha384
    HASHFUNC_NAME = SHA384


class SECP256k1Signer(NIST_ECDSASigner):
    CURVE = ecdsa.SECP256k1
    CURVE_NAME = SECP256k1


def get_signer(curve):
    if curve == NIST256p:
        return NIST256pSigner
    elif curve == NIST384p:
        return NIST384pSigner
    elif curve == SECP256k1:
        return SECP256k1Signer
    else:
        raise Exception("Unknown curve: %s" % str(curve))
