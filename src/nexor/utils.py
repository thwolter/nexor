import hashlib
import json
import os
import warnings
from typing import Any, ClassVar, Sequence

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings


def parse_cors_origins(value: str | list[str] | None) -> tuple[str, ...]:
    if not value:
        return ()
    if value in ('*', '"*"'):
        return ('*',)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, str):
                return (parsed.strip().rstrip('/'),)
            if isinstance(parsed, (list, tuple)):
                return tuple(o.strip().rstrip('/') for o in parsed)
        except json.JSONDecodeError:
            return tuple(o.strip().rstrip('/') for o in value.split(',') if o.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(o).strip().rstrip('/') for o in value)
    return (str(value).strip().rstrip('/'),)


def _check_missing_keys(
    s: BaseSettings | BaseModel,
    *,
    sub_key: str = '',
    raise_on_missing: bool = True,
) -> list[str]:
    env = os.getenv('ENV', '').lower()
    testing_mode = env.startswith('test')
    missing: list[str] = []

    for key in getattr(s, 'required_keys', []):
        value = getattr(s, key, None)
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not value or not str(value).strip():
            if sub_key:
                name = f'{sub_key.upper()}__{key.upper()}'
            else:
                name = f'{key.upper()}'
            missing.append(name)

    for field_key, field_value in s.__dict__.items():
        if isinstance(field_value, (ValidatedSettings, ValidatedModel)):
            missing += _check_missing_keys(field_value, sub_key=field_key)

    if missing and raise_on_missing and not sub_key:
        message = f'Missing required environment keys: {", ".join(missing)}'
        if testing_mode:
            warnings.warn(message)
        else:
            raise RuntimeError(message)

    return missing


class ValidatedSettings(BaseSettings):
    required_keys: ClassVar[list[str]] = []

    def model_post_init(self, context: Any, /) -> None:
        _check_missing_keys(self)


class ValidatedModel(BaseModel):
    required_keys: ClassVar[list[str]] = []

    def model_post_init(self, context: Any, /) -> None:
        _check_missing_keys(self, raise_on_missing=False)


class FingerprintMixin(BaseModel):
    fingerprint_keys: ClassVar[Sequence[str] | None] = None
    fingerprint_exclude: ClassVar[Sequence[str] | None] = None

    def get_fingerprint(self) -> str:
        include_set = set(self.fingerprint_keys) if self.fingerprint_keys is not None else None
        exclude_set = set(self.fingerprint_exclude) if self.fingerprint_exclude is not None else None

        if include_set and exclude_set:
            overlap = include_set & exclude_set
            if overlap:
                joined = ', '.join(sorted(overlap))
                raise ValueError(
                    f'Fingerprint keys appear in both include and exclude: {joined}'
                )

        model_fields = set(type(self).model_fields)
        if include_set is not None:
            invalid_includes = include_set - model_fields
            if invalid_includes:
                joined = ', '.join(sorted(invalid_includes))
                raise ValueError(
                    f'Fingerprint include references unknown fields: {joined}'
                )

        if exclude_set is not None:
            invalid_excludes = exclude_set - model_fields
            if invalid_excludes:
                joined = ', '.join(sorted(invalid_excludes))
                raise ValueError(
                    f'Fingerprint exclude references unknown fields: {joined}'
                )

        payload = self.model_dump(include=include_set, exclude=exclude_set, mode='json')
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()


def normalize_postgres_url(url: str | None) -> str | None:
    """Return a normalized `postgresql://` URL (or the original value)."""
    if url is None:
        return None
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url
