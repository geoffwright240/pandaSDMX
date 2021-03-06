# encoding: utf-8


from pandasdmx.utils import DictLike
from pandasdmx import model
from .common import Reader
from lxml import objectify
from lxml.etree import XPath



 
class SDMXMLReader(Reader):

    
    """
    Read SDMX-ML 2.1 and expose it as instances from pandasdmx.model
    """
    
    _nsmap = {
            'com': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
            'str': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
            'mes': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message'
    }

    def initialize(self, source):
        root = objectify.parse(source).getroot()
        if root.tag.endswith('Structure'):
            cls = model.StructureMessage
        elif root.tag.endswith('GenericData'):
            cls = model.DataMessage
        self.message = cls(self, root)  
        return self.message 
    
    
    @staticmethod     
    def get_dataset(reader, elem):
        if elem.tag.endswith('GenericData'):
            cls = model.GenericDataSet
        elif elem.tag.endswith('StructureSpecificData'):
            cls = model.StructureSpecificDataSet
        return cls(reader, elem.DataSet)  
            

    _model_map = {
        'header' : (XPath('mes:Header', namespaces = _nsmap), model.Header),
        'footer' : (XPath('mes:Footer', namespaces = _nsmap), model.Footer), 
        'annotations' : (XPath('com:Annotations/com:Annotation', 
                             namespaces = _nsmap), model.Annotation),
        'codelists' : (XPath('mes:Structures/str:Codelists/str:Codelist', 
                             namespaces = _nsmap), model.Codelist),
                  'codes': (XPath('str:Code', 
                             namespaces = _nsmap), model.Code),  
                  'conceptschemes' : (XPath('mes:Structures/str:Concepts/str:ConceptScheme', 
                             namespaces = _nsmap), model.ConceptScheme),
        'concepts' : (XPath('str:Concept', 
                             namespaces = _nsmap), model.Concept),
        'categoryschemes' : (XPath('mes:Structures/str:CategorySchemes/str:CategoryScheme', 
                             namespaces = _nsmap), model.CategoryScheme),
        'categories': (XPath('str:Category', 
                             namespaces = _nsmap), model.Category),  
        'dataflows' : (XPath('mes:Structures/str:Dataflows/str:Dataflow', 
                             namespaces = _nsmap), model.DataflowDefinition),
        'datastructures' : (XPath('mes:Structures/str:DataStructures/str:DataStructure', 
                             namespaces = _nsmap), model.DataStructureDefinition),
        'dimdescriptor' : (XPath('str:DataStructureComponents/str:DimensionList', 
                             namespaces = _nsmap), model.DimensionDescriptor),
        'dimensions': (XPath('str:Dimension', 
                             namespaces = _nsmap), model.Dimension),
        'time_dimension': (XPath('str:TimeDimension', 
                             namespaces = _nsmap), model.TimeDimension),
        'measure_dimension': (XPath('str:MeasureDimension', 
                             namespaces = _nsmap), model.MeasureDimension),
        'measures' : (XPath('str:DataStructureComponents/str:MeasureList', 
                             namespaces = _nsmap), model.MeasureDescriptor),
        'measure_items' : (XPath('str:PrimaryMeasure', 
                             namespaces = _nsmap), model.PrimaryMeasure), 
        'attributes' : (XPath('str:DataStructureComponents/str:AttributeList', 
                             namespaces = _nsmap), model.AttributeDescriptor),
                  'attribute_items' : (XPath('str:Attribute', 
                             namespaces = _nsmap), model.DataAttribute),
                  'data' : (XPath('mes:DataSet', 
                             namespaces = _nsmap), get_dataset),
    } 
        
        
    def read(self, name, sdmxobj):
        path, cls = self._model_map[name]
        try:
            return cls(self, path(sdmxobj._elem)[0])
        except IndexError:
            return None
     
     
    def read_dict(self, name, sdmxobj):
        '''
        If sdmxobj inherits from dict: update it  with modelized elements. 
        These must be instances of model.IdentifiableArtefact,
        i.e. have an 'id' attribute. This will be used as dict keys.
        If sdmxobj does not inherit from dict: return a new DictLike. 
        '''
        path, cls = self._model_map[name]
        result = {e.get('id') : cls(self, e) for e in path(sdmxobj._elem)}
        if isinstance(sdmxobj, dict): sdmxobj.update(result)
        else: return DictLike(result)
        

    def header_id(self, sdmxobj):
        return sdmxobj._elem.ID[0].text 

    def identity(self, sdmxobj):
        return sdmxobj._elem.get('id')
    
    def urn(self, sdmxobj):
        return sdmxobj._elem.get('urn')

    def uri(self, sdmxobj):
        return sdmxobj._elem.get('uri')
        
        
    def agencyID(self, sdmxobj):
        return sdmxobj._elem.get('agencyID')
    
    
    def attributes_to_dict(self, name, sdmxobj):
        elem_attrib = sdmxobj._elem.xpath('com:{0}/@xml:lang'.format(name), 
                               namespaces = self._nsmap)
        values = sdmxobj._elem.xpath('com:{0}/text()'.format(name), 
                             namespaces = self._nsmap)
        return DictLike(zip(elem_attrib, values))

    def header_prepared(self, sdmxobj):
        return sdmxobj._elem.Prepared[0].text # convert this to datetime obj?
        
    def header_sender(self, sdmxobj):
        return DictLike(sdmxobj._elem.Sender.attrib)

    def header_error(self, sdmxobj):
        try:
            return DictLike(sdmxobj._elem.Error.attrib)
        except AttributeError: return None
                     
        
    def isfinal(self, sdmxobj):
        return bool(sdmxobj._elem.get('isFinal')) 
        
    def concept_id(self, sdmxobj):
        # called by model.Component.concept
        c_id = sdmxobj._elem.xpath('str:ConceptIdentity/Ref/@id', 
                          namespaces = self._nsmap)[0]
        parent_id = sdmxobj._elem.xpath('str:ConceptIdentity/Ref/@maintainableParentID',
                               namespaces = self._nsmap)[0]
        return self.message.conceptschemes[parent_id][c_id]
        
    def position(self, sdmxobj):
        # called by model.Dimension
        return int(sdmxobj._elem.get('position')) 
    
    def localrepr(self, sdmxobj):
        node = sdmxobj._elem.xpath('str:LocalRepresentation',
                          namespaces = self._nsmap)[0]
        enum = node.xpath('str:Enumeration/Ref/@id',
                          namespaces = self._nsmap)
        if enum: enum = self.message.codelists[enum[0]]
        else: enum = None
        return model.Representation(self, node, enum = enum)
    
    def assignment_status(self, sdmxobj):
        return sdmxobj._elem.get('assignmentStatus')
        
    def attr_relationship(self, sdmxobj):
        return sdmxobj._elem.xpath('*/Ref/@id')
    
            
                 
    def parse_series(self, source):
        """
        generator to parse data from xml. Iterate over series
        """
        CodeTuple = None
        generic_ns = '{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}'
        series_tag = generic_ns + 'Series'
        serieskey_tag = series_tag + 'Key'
        value_tag = generic_ns + 'Value'
        obs_tag = generic_ns + 'Obs'
        obsdim_tag = generic_ns + 'ObsDimension'
        obsvalue_tag = generic_ns + 'ObsValue'
        attributes_tag = generic_ns + 'Attributes' 
        context = lxml.etree.iterparse(source, tag = series_tag)
        
        for _, series in context: 
            raw_dates, raw_values, raw_status = [], [], []
            
            for elem in series.iterchildren():
                if sdmxobj._elem.tag == serieskey_tag:
                    code_keys, code_values = [], []
                    for value in sdmxobj._elem.iter(value_tag):
                        if not CodeTuple: code_keys.append(value.get('id')) 
                        code_values.append(value.get('value'))
                elif sdmxobj._elem.tag == obs_tag:
                    for elem1 in sdmxobj._elem.iterchildren():
                        observation_status = 'A'
                        if elem1.tag == obsdim_tag:
                            dimension = elem1.get('value')
                            # Prepare time spans such as Q1 or S2 to make it parsable
                            suffix = dimension[-2:]
                            if suffix in time_spans:
                                dimension = dimension[:-2] + time_spans[suffix]
                            raw_dates.append(dimension) 
                        elif elem1.tag == obsvalue_tag:
                            value = elem1.get('value')
                            raw_values.append(value)
                        elif elem1.tag == attributes_tag:
                            for elem2 in elem1.iter(".//"+generic_ns+"Value[@id='OBS_STATUS']"):
                                observation_status = elem2.get('value')
                            raw_status.append(observation_status)
            if not CodeTuple:
                CodeTuple = make_namedtuple(code_keys) 
            codes = CodeTuple._make(code_values)
            series.clear()
            yield codes, raw_dates, raw_values, raw_status 
    
