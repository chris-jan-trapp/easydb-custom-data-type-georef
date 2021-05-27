import xml.etree.ElementTree as ET
import requests
import json


class WFSClient:
    RESPONSE_NAMESPACE = {"wfs": "http://www.opengis.net/wfs",
                          "ogc": "http://www.opengis.net/ogc"
                          }

    def __init__(self, server_url, transaction_attributes, object_type, fields, geometry_field):
        self.server_url = server_url
        self.transaction_attributes = transaction_attributes
        self.feature_type = object_type
        self.fields = fields
        self.geometry_field = geometry_field

    def get_create_xml(self, feature):
        transaction = ET.Element("wfs:Transaction", **self.transaction_attributes)
        insert = ET.SubElement(transaction, "wfs:Insert")
        to_insert = ET.SubElement(insert, ":".join((self.transaction_attributes["xmlns:gbv"], self.feature_type)))
        for field in WFSClient.get_fields(feature):
            node = ET.SubElement(to_insert, field)
            node.text = feature.get(field)
        if self.geometry_field in feature.keys():
            to_insert.append(self.get_gml(feature))
        return ET.tostring(transaction)

    def get_update_xml(self, feature, feature_id):
        transaction = ET.Element("wfs:Transaction", self.transaction_attributes)
        type_name = "gbv:" + self.feature_type
        update = ET.SubElement(transaction, "wfs:Update", typeName=type_name)
        for field in WFSClient.get_fields(feature, self.fields):
            property = ET.SubElement(update, "wfs:Property")
            name = ET.SubElement(property, "wfs:Name")
            name.text = field
            value = ET.SubElement(property, "wfs:Value")
            value.text = feature[field]
        selector = ET.SubElement(update, "ogc:Filter")
        ET.SubElement(selector, "ogc:FeatureId", fid=feature_id)
        return ET.tostring(transaction)


    @classmethod
    def get_fields(cls, feature, fields):
        populated_fields = filter(lambda k: k in feature.keys(), fields)
        return populated_fields

    def get_gml(self, feature):
        geometry = ET.Element(self.geometry_field)
        point_property_type = ET.SubElement(geometry, 'gml:PointPropertyType', srsName="EPSG:4326")
        pos = ET.SubElement(point_property_type, 'gml:pos')
        concept_uri = json.loads(feature[self.geometry_field]['conceptURI'])
        coordinates = concept_uri['geometry']['coordinates']
        pos.text = str(coordinates[0]) + ' ' + str(coordinates[1])
        return geometry

    def post_transaction(self, data):
        return requests.post(self.server_url, data=data, headers={"Content-type": "text/xml"})

    def create_feature(self, feature):
        data = self.get_create_xml(feature)
        response = self.post_transaction(data)

        if response.status_code == 200:
            transaction_result = ET.fromstring(response.content)
            feature_id = transaction_result.find("**/ogc:FeatureId", WFSClient.RESPONSE_NAMESPACE)
            return feature_id.get('fid')
        else:
            raise ValueError("Create failed with: " + str(response.content))

    def update_feature(self, feature, feature_id):
        data = self.get_update_xml(feature, feature_id)
        response = self.post_transaction(data)

        if not response.status_code == 200:
            raise ValueError("Update failed wit: " + str(response.content))