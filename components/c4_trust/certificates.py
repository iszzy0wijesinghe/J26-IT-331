from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.x509.oid import ExtensionOID, NameOID


@dataclass(frozen=True)
class CertificateValidationResult:
    """Outcome of validating an X.509 device certificate."""

    is_valid: bool
    reason_code: str
    certificate: x509.Certificate | None = None
    public_key: ec.EllipticCurvePublicKey | None = None
    error_detail: str | None = None


def load_certificate(cert_data: x509.Certificate | bytes | str) -> x509.Certificate:
    """Load an X.509 certificate from an object, PEM string, or PEM/DER bytes."""
    if isinstance(cert_data, x509.Certificate):
        return cert_data

    if isinstance(cert_data, str):
        return x509.load_pem_x509_certificate(cert_data.encode("utf-8"))

    if isinstance(cert_data, bytes):
        try:
            return x509.load_pem_x509_certificate(cert_data)
        except Exception:
            return x509.load_der_x509_certificate(cert_data)

    raise TypeError(f"Unsupported certificate data type: {type(cert_data).__name__}")


class X509CertificateValidator:
    """Validates X.509 device certificates for GeoNex C4 trust assessment."""

    def __init__(
        self,
        trusted_ca_certificates: Sequence[x509.Certificate | bytes | str] | None = None,
        *,
        revoked_serial_numbers: Sequence[int] | set[int] | None = None,
        crls: Sequence[x509.CertificateRevocationList] | None = None,
        require_key_usage: bool = True,
        allow_self_signed: bool = False,
    ) -> None:
        self._trusted_cas: list[x509.Certificate] = []
        if trusted_ca_certificates:
            for ca_data in trusted_ca_certificates:
                self._trusted_cas.append(load_certificate(ca_data))

        self._revoked_serials: set[int] = set(revoked_serial_numbers or ())
        self._crls: list[x509.CertificateRevocationList] = list(crls or ())
        self._require_key_usage = require_key_usage
        self._allow_self_signed = allow_self_signed

    def add_trusted_ca(self, ca_data: x509.Certificate | bytes | str) -> None:
        self._trusted_cas.append(load_certificate(ca_data))

    def revoke_serial(self, serial_number: int) -> None:
        self._revoked_serials.add(serial_number)

    def is_serial_revoked(self, serial_number: int) -> bool:
        if serial_number in self._revoked_serials:
            return True
        for crl in self._crls:
            revoked_cert = crl.get_revoked_certificate_by_serial_number(serial_number)
            if revoked_cert is not None:
                return True
        return False

    def validate(
        self,
        cert_data: x509.Certificate | bytes | str,
        expected_device_id: str,
        *,
        now: datetime | None = None,
    ) -> CertificateValidationResult:
        check_time = now or datetime.now(UTC)
        if check_time.tzinfo is None or check_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        try:
            cert = load_certificate(cert_data)
        except Exception as exc:
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_MALFORMED",
                error_detail=f"Certificate parsing failed: {exc}",
            )

        if self.is_serial_revoked(cert.serial_number):
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_REVOKED",
                certificate=cert,
                error_detail=f"Certificate with serial {cert.serial_number} is revoked",
            )

        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc

        if check_time < not_before:
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_NOT_YET_VALID",
                certificate=cert,
                error_detail=f"Certificate not valid before {not_before.isoformat()}",
            )

        if check_time > not_after:
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_EXPIRED",
                certificate=cert,
                error_detail=f"Certificate expired at {not_after.isoformat()}",
            )

        is_self_signed = cert.issuer == cert.subject
        issuer_ca: x509.Certificate | None = None

        for ca in self._trusted_cas:
            if ca.subject == cert.issuer:
                issuer_ca = ca
                break

        if issuer_ca is None:
            if is_self_signed and not self._allow_self_signed:
                return CertificateValidationResult(
                    is_valid=False,
                    reason_code="CERTIFICATE_SELF_SIGNED",
                    certificate=cert,
                    error_detail="Self-signed certificate is not explicitly trusted",
                )
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_UNTRUSTED_ISSUER",
                certificate=cert,
                error_detail=f"Issuer '{cert.issuer.rfc4514_string()}' not in trusted CA store",
            )

        try:
            ca_public_key = issuer_ca.public_key()
            if isinstance(ca_public_key, ec.EllipticCurvePublicKey):
                ca_public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    ec.ECDSA(cert.signature_hash_algorithm),
                )
            elif isinstance(ca_public_key, rsa.RSAPublicKey):
                ca_public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )
            else:
                return CertificateValidationResult(
                    is_valid=False,
                    reason_code="CERTIFICATE_CHAIN_INVALID",
                    certificate=cert,
                    error_detail=f"Unsupported CA key type: {type(ca_public_key).__name__}",
                )
        except InvalidSignature:
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_CHAIN_INVALID",
                certificate=cert,
                error_detail="Certificate signature verification failed against issuer CA",
            )
        except Exception as exc:
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_CHAIN_INVALID",
                certificate=cert,
                error_detail=f"Certificate chain validation error: {exc}",
            )

        cn_attributes = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        subject_cns = [
            attr.value for attr in cn_attributes if isinstance(attr.value, str)
        ]

        san_names: list[str] = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            for name in san_ext.value:
                if isinstance(name, x509.DNSName):
                    san_names.append(name.value)
                elif isinstance(name, x509.UniformResourceIdentifier):
                    uri = name.value
                    if uri.startswith("urn:geonex:device:"):
                        san_names.append(uri.removeprefix("urn:geonex:device:"))
                    else:
                        san_names.append(uri)
        except x509.ExtensionNotFound:
            pass

        device_matched = (expected_device_id in subject_cns) or (
            expected_device_id in san_names
        )

        if not device_matched:
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_IDENTITY_MISMATCH",
                certificate=cert,
                error_detail=(
                    f"Device ID '{expected_device_id}' does not match "
                    f"certificate CNs {subject_cns} or SANs {san_names}"
                ),
            )

        try:
            bc_ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.BASIC_CONSTRAINTS
            )
            if bc_ext.value.ca:
                return CertificateValidationResult(
                    is_valid=False,
                    reason_code="CERTIFICATE_KEY_USAGE_INVALID",
                    certificate=cert,
                    error_detail="CA certificate presented as device telemetry certificate",
                )
        except x509.ExtensionNotFound:
            pass

        if self._require_key_usage:
            try:
                ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
                if not ku_ext.value.digital_signature:
                    return CertificateValidationResult(
                        is_valid=False,
                        reason_code="CERTIFICATE_KEY_USAGE_INVALID",
                        certificate=cert,
                        error_detail="Certificate lacks digital_signature key usage",
                    )
            except x509.ExtensionNotFound:
                pass

        public_key = cert.public_key()
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return CertificateValidationResult(
                is_valid=False,
                reason_code="CERTIFICATE_KEY_USAGE_INVALID",
                certificate=cert,
                error_detail="Certificate public key must be an elliptic curve key for ECDSA",
            )

        return CertificateValidationResult(
            is_valid=True,
            reason_code="CERTIFICATE_VALID",
            certificate=cert,
            public_key=public_key,
        )


def create_ca(
    common_name: str = "GeoNex Root CA",
    *,
    valid_days: int = 365,
    issued_at: datetime | None = None,
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate, bytes]:
    """Generate a self-signed Root CA key pair and certificate for simulation and tests."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GeoNex Research"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Component 4 CA"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )
    now = issued_at or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("issued_at must be timezone-aware")
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=1),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return private_key, cert, cert_pem


def create_device_certificate(
    device_id: str,
    ca_cert: x509.Certificate,
    ca_key: ec.EllipticCurvePrivateKey,
    *,
    valid_days: int = 30,
    not_before_offset_days: int = 0,
    digital_signature: bool = True,
    is_ca: bool = False,
    san_dns_names: Sequence[str] | None = None,
    private_key: ec.EllipticCurvePrivateKey | None = None,
    issued_at: datetime | None = None,
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate, bytes]:
    """Generate a device certificate signed by the specified CA."""
    dev_key = private_key or ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GeoNex Sensors"),
            x509.NameAttribute(NameOID.COMMON_NAME, device_id),
        ]
    )
    now = issued_at or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("issued_at must be timezone-aware")
    not_before = now + timedelta(days=not_before_offset_days)
    not_after = not_before + timedelta(days=valid_days)

    sans: list[x509.GeneralName] = [
        x509.DNSName(device_id),
        x509.UniformResourceIdentifier(f"urn:geonex:device:{device_id}"),
    ]
    if san_dns_names:
        for dns_name in san_dns_names:
            sans.append(x509.DNSName(dns_name))

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(dev_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(
            x509.BasicConstraints(ca=is_ca, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName(sans),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=digital_signature,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=is_ca,
                crl_sign=is_ca,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    )

    cert = builder.sign(ca_key, hashes.SHA256())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    return dev_key, cert, cert_pem


def create_crl(
    ca_cert: x509.Certificate,
    ca_key: ec.EllipticCurvePrivateKey,
    revoked_serials: Sequence[int],
    *,
    valid_days: int = 7,
) -> x509.CertificateRevocationList:
    """Generate an X.509 Certificate Revocation List (CRL) for revoked devices."""
    now = datetime.now(UTC)
    builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(ca_cert.subject)
        .last_update(now - timedelta(minutes=5))
        .next_update(now + timedelta(days=valid_days))
    )
    for serial in revoked_serials:
        revoked_cert = (
            x509.RevokedCertificateBuilder()
            .serial_number(serial)
            .revocation_date(now - timedelta(minutes=1))
            .build()
        )
        builder = builder.add_revoked_certificate(revoked_cert)

    return builder.sign(ca_key, hashes.SHA256())
