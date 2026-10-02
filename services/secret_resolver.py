import json
import logging
from typing import Optional, Tuple

# Optional imports for vault integrations
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:
    boto3 = None

try:
    import hvac
except Exception:
    hvac = None

try:
    from google.cloud import secretmanager
except Exception:
    secretmanager = None

logger = logging.getLogger(__name__)


def _is_vault_ref(value: Optional[str]) -> bool:
    return isinstance(value, str) and (value.startswith("vault://") or value.startswith("aws-sm://"))

def _parse_vault_ref(ref: str) -> Tuple[str, str]:
    if "#" in ref:
        base, key = ref.split("#", 1)
    else:
        base, key = ref, ""
    return base, key

async def resolve_secret(ref: str, settings: ServersSettings) -> Optional[str]:
    """
    Resolve a secret reference. Supports:
      - aws-sm://secret-name[#json_key]
      - vault://path/to/secret[#key]
    Returns resolved string or None on failure.
    """
    if ref.startswith("aws-sm://"):
        if boto3 is None:
            raise RuntimeError("boto3 not installed for AWS Secrets Manager resolution")
        secret_name, json_key = _parse_vault_ref(ref.replace("aws-sm://", "", 1))
        try:
            client = boto3.client("secretsmanager", region_name=settings.aws_region)
            resp = client.get_secret_value(SecretId=secret_name)
            secret_string = resp.get("SecretString")
            if not secret_string:
                return None
            if json_key:
                try:
                    data = json.loads(secret_string)
                    return data.get(json_key)
                except Exception:
                    return None
            return secret_string
        except (BotoCoreError, ClientError) as e:
            logger.exception("AWS SM error resolving %s: %s", ref, e)
            return None

    if ref.startswith("vault://"):
        if hvac is None:
            raise RuntimeError("hvac not installed for HashiCorp Vault resolution")
        path, key = _parse_vault_ref(ref.replace("vault://", "", 1))
        try:
            client = hvac.Client(url=settings.hashicorp_addr, token=settings.hashicorp_token)
            # Try KV v2 first, fallback to v1
            try:
                resp = client.secrets.kv.v2.read_secret_version(path=path)
                data = resp["data"]["data"]
            except Exception:
                resp = client.secrets.kv.v1.read_secret(path=path)
                data = resp.get("data", {})
            if key:
                return data.get(key)
            if isinstance(data, dict) and len(data) == 1:
                return next(iter(data.values()))
            return json.dumps(data)
        except Exception as e:
            logger.exception("Vault error resolving %s: %s", ref, e)
            return None
        
    if ref.startswith("gcp-sm://"):
        if secretmanager is None:
            raise RuntimeError("google-cloud-secret-manager not installed")
        name, json_key = _parse_vault_ref(ref.replace("gcp-sm://", "", 1))
        try:
            client = secretmanager.SecretManagerServiceClient()
            resp = client.access_secret_version(request={"name": name})
            secret_string = resp.payload.data.decode("utf-8")
            if json_key:
                data = json.loads(secret_string)
                return data.get(json_key)
            return secret_string
        except Exception as e:
            logger.exception("GCP SM error resolving %s: %s", ref, e)
            return None

    # not a vault ref -> return as-is
    return ref