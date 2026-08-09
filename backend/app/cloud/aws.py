"""Read-only AWS connector. Only resources tagged quorom:managed=true."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings


@dataclass
class ManagedResource:
    resource_id: str
    resource_type: str  # ec2 | lambda
    resource_name: str
    resource_arn: str
    region: str
    metadata: dict[str, Any] = field(default_factory=dict)


class AwsSandboxClient:
    """
    Read-only boto3 wrapper scoped to the Quorom sandbox tag.

    Day 1: list + metrics only. No stop/terminate/modify calls.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.tag_key = self.settings.aws_sandbox_tag_key
        self.tag_value = self.settings.aws_sandbox_tag_value
        self.region = self.settings.aws_region
        session_kwargs: dict[str, Any] = {"region_name": self.region}
        if self.settings.aws_access_key_id and self.settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = self.settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = self.settings.aws_secret_access_key
        self._session = boto3.Session(**session_kwargs)

    def _ec2(self):
        return self._session.client("ec2")

    def _lambda(self):
        return self._session.client("lambda")

    def _cloudwatch(self):
        return self._session.client("cloudwatch")

    def list_managed_ec2(self) -> list[ManagedResource]:
        """List EC2 instances with the hard sandbox tag filter."""
        filters = [
            {"Name": f"tag:{self.tag_key}", "Values": [self.tag_value]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
        try:
            paginator = self._ec2().get_paginator("describe_instances")
            resources: list[ManagedResource] = []
            for page in paginator.paginate(Filters=filters):
                for reservation in page.get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                        if tags.get(self.tag_key) != self.tag_value:
                            continue
                        name = tags.get("Name", inst["InstanceId"])
                        resources.append(
                            ManagedResource(
                                resource_id=inst["InstanceId"],
                                resource_type="ec2",
                                resource_name=name,
                                resource_arn=inst.get("InstanceArn")
                                or f"arn:aws:ec2:{self.region}:instance/{inst['InstanceId']}",
                                region=self.region,
                                metadata={
                                    "instance_type": inst.get("InstanceType"),
                                    "state": inst.get("State", {}).get("Name"),
                                    "launch_time": str(inst.get("LaunchTime", "")),
                                    "tags": tags,
                                },
                            )
                        )
            return resources
        except (ClientError, BotoCoreError) as exc:
            raise RuntimeError(f"Failed to list managed EC2: {exc}") from exc

    def list_managed_lambda(self) -> list[ManagedResource]:
        """List Lambda functions that carry the sandbox tag."""
        try:
            paginator = self._lambda().get_paginator("list_functions")
            resources: list[ManagedResource] = []
            for page in paginator.paginate():
                for fn in page.get("Functions", []):
                    name = fn["FunctionName"]
                    try:
                        tag_resp = self._lambda().list_tags(Resource=fn["FunctionArn"])
                        tags = tag_resp.get("Tags", {})
                    except (ClientError, BotoCoreError):
                        continue
                    if tags.get(self.tag_key) != self.tag_value:
                        continue
                    resources.append(
                        ManagedResource(
                            resource_id=name,
                            resource_type="lambda",
                            resource_name=name,
                            resource_arn=fn["FunctionArn"],
                            region=self.region,
                            metadata={
                                "runtime": fn.get("Runtime"),
                                "memory_mb": fn.get("MemorySize"),
                                "timeout": fn.get("Timeout"),
                                "last_modified": fn.get("LastModified"),
                                "tags": tags,
                            },
                        )
                    )
            return resources
        except (ClientError, BotoCoreError) as exc:
            raise RuntimeError(f"Failed to list managed Lambda: {exc}") from exc

    def list_managed_resources(self) -> list[ManagedResource]:
        return self.list_managed_ec2() + self.list_managed_lambda()
