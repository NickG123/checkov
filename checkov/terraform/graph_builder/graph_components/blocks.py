import os
from typing import Union, Dict, Any, List, Optional, Set

from checkov.common.graph.graph_builder.graph_components.blocks import Block
from checkov.common.util.consts import RESOLVED_MODULE_ENTRY_NAME
from checkov.terraform.graph_builder.graph_components.block_types import BlockType
from checkov.terraform.graph_builder.utils import remove_module_dependency_in_path


class TerraformBlock(Block):
    __slots__ = ("module_connections", "module_dependency", "module_dependency_num", "source_module", "has_dynamic_block")

    def __init__(self, name: str, config: Dict[str, Any], path: str, block_type: BlockType, attributes: Dict[str, Any],
                 id: str = "", source: str = "", has_dynamic_block: bool = False) -> None:
        """
            :param name: unique name given to the terraform block, for example: 'aws_vpc.example_name'
            :param config: the section in tf_definitions that belong to this block
            :param path: the file location of the block
            :param block_type: BlockType
            :param attributes: dictionary of the block's original attributes in the terraform file
        """
        super(TerraformBlock, self).__init__(name, config, path, block_type, attributes, id, source)
        self.module_dependency = ""
        self.module_dependency_num = ""
        if path:
            self.path, module_dependency, num = remove_module_dependency_in_path(path)
            self.path = os.path.realpath(self.path)
            if module_dependency:
                self.module_dependency = module_dependency
                self.module_dependency_num = num
        if attributes.get(RESOLVED_MODULE_ENTRY_NAME):
            del attributes[RESOLVED_MODULE_ENTRY_NAME]
        self.attributes = attributes
        self.module_connections: Dict[str, List[int]] = {}
        self.source_module: Set[int] = set()
        self.has_dynamic_block = has_dynamic_block

    def add_module_connection(self, attribute_key: str, vertex_id: int) -> None:
        self.module_connections.setdefault(attribute_key, []).append(vertex_id)

    def find_attribute(self, attribute: Optional[Union[str, List[str]]]) -> Optional[str]:
        """
        :param attribute: key to search in self.attributes
        The function searches for  attribute in self.attribute. It might not exist if the block is variable or output,
        or its search path might be different if its a resource.
        :return: the actual attribute key or None
        """
        if not attribute:
            return None

        if self.attributes.get(attribute[0]):
            return attribute[0]

        if self.block_type == BlockType.VARIABLE:
            return "default" if self.attributes.get("default") else None

        if self.block_type == BlockType.OUTPUT:
            return "value" if self.attributes.get("value") else None

        if self.block_type == BlockType.RESOURCE and len(attribute) > 1:
            # handle cases where attribute_at_dest == ['aws_s3_bucket.template_bucket', 'acl']
            if self.name == attribute[0] and self.attributes.get(attribute[1]):
                return attribute[1]

        return None

    @classmethod
    def get_inner_attributes(
        cls,
        attribute_key: str,
        attribute_value: Union[str, List[str], Dict[str, Any]],
        strip_list: bool = True
    ) -> Dict[str, Any]:
        if strip_list and isinstance(attribute_value, list) and len(attribute_value) == 1:
            attribute_value = attribute_value[0]

        return super().get_inner_attributes(
            attribute_key=attribute_key,
            attribute_value=attribute_value,
        )
