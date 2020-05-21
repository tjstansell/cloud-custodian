# Copyright 2016-2017 Capital One Services, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from c7n.actions import BaseAction
from c7n.manager import resources
from c7n.query import QueryResourceManager, DescribeSource, ConfigSource, TypeInfo
from c7n.tags import universal_augment
from c7n.utils import type_schema


class DescribeCertificate(DescribeSource):

    def augment(self, resources):
        return universal_augment(
            self.manager,
            super(DescribeCertificate, self).augment(resources))


@resources.register('acm-certificate')
class Certificate(QueryResourceManager):

    class resource_type(TypeInfo):
        service = 'acm'
        enum_spec = (
            'list_certificates',
            'CertificateSummaryList',
            {'Includes': {
                'keyTypes': [
                    'RSA_2048', 'RSA_1024', 'RSA_4096',
                    'EC_prime256v1', 'EC_secp384r1',
                    'EC_secp521r1']}})
        id = 'CertificateArn'
        name = 'DomainName'
        date = 'CreatedAt'
        detail_spec = (
            "describe_certificate", "CertificateArn",
            'CertificateArn', 'Certificate')
        cfn_type = "AWS::CertificateManager::Certificate"
        config_type = "AWS::ACM::Certificate"
        arn_type = 'certificate'
        universal_taggable = object()

    source_mapping = {
        'describe': DescribeCertificate,
        'config': ConfigSource
    }


@Certificate.action_registry.register('delete')
class CertificateDeleteAction(BaseAction):
    """Action to delete an ACM Certificate
    To avoid unwanted deletions of certificates, it is recommended to apply a filter
    to the rule
    :example:

    .. code-block:: yaml

        policies:
          - name: acm-certificate-delete-expired
            resource: acm-certificate
            filters:
              - type: value
                key: NotAfter
                value_type: expiration
                op: lt
                value: 0
            actions:
              - delete
    """

    schema = type_schema('delete')
    permissions = (
        "acm:DeleteCertificate",
    )

    def process(self, certificates):
        return self._process_with_futures(self.process_cert, certificates)

    def process_cert(self, cert):
        try:
            self.manager.retry(
                self.client.delete_certificate, CertificateArn=cert['CertificateArn']
            )
            self.results.ok(cert)
        except self.client.exceptions.ResourceNotFoundException as e:
            self.results.skip(cert, e)
            pass
        except self.client.exceptions.ResourceInUseException as e:
            self.log.warning(
                "Exception trying to delete Certificate: %s error: %s",
                cert['CertificateArn'], e)
            self.results.error(cert, e)
