from app.core.masking import mask_dict, mask_identifier, mask_text
from app.core.security import (
    Permission,
    create_access_token,
    decode_access_token,
    decrypt_value,
    encrypt_value,
    hash_password,
    permissions_for,
    verify_password,
)


def test_password_hashing_roundtrip():
    h = hash_password("Correct-Horse-9")
    assert h != "Correct-Horse-9"
    assert verify_password("Correct-Horse-9", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip_and_tamper():
    token = create_access_token("user-1", ["customer"])
    assert decode_access_token(token)["sub"] == "user-1"
    assert decode_access_token(token[:-2] + "xx") is None
    assert decode_access_token(create_access_token("u", ["customer"], minutes=-1)) is None


def test_field_encryption():
    enc = encrypt_value("BPX448120931")
    assert "BPX448120931" not in enc
    assert decrypt_value(enc) == "BPX448120931"


def test_masking():
    assert mask_text("call 512-555-0182 or a@b.com") == "call [PHONE] or [EMAIL]"
    assert mask_identifier("NSM-AU-4471923").endswith("1923")
    assert mask_dict({"password": "x", "nested": {"member_id": "1"}}) == {"password": "[REDACTED]", "nested": {"member_id": "[REDACTED]"}}


def test_rbac():
    assert Permission.AI_APPROVE in permissions_for(["customer"])
    assert Permission.EVAL_READ not in permissions_for(["customer"])
    assert Permission.EVAL_READ in permissions_for(["analyst"])
    assert permissions_for(["unknown-role"]) == set()
