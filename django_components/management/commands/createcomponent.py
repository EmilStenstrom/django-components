from typing import Any
from django.core.management.base import BaseCommand,CommandParser
from django.conf import settings
from pathlib import Path
from django.utils.text import capfirst,get_valid_filename
from django.template import Context, Template

THIS_DIR = Path(__file__).parent
BASE_DIR:Path = getattr(settings,'BASE_DIR')
COMP_FOLDER = BASE_DIR.joinpath('components')

if not COMP_FOLDER.exists:
    COMP_FOLDER.mkdir()
    
class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('component_name',type=str,help='component name')
    
    def create_file(self,file_path,content:str):
        with open(file_path,'w') as file:
            file.write(content)
    
    def handle(self, component_name:str, **options: Any):
        camelCase = capfirst(component_name)
        file_name = get_valid_filename(component_name)
        context = Context({
            'name':camelCase,
            'file_name':file_name
        })
        with open(THIS_DIR/'templates'/'{comp_name}.py.txt') as file:
            template = Template(file.read())
        py_file = template.render(context)
        comp_path = COMP_FOLDER.joinpath(file_name)
        
        if not comp_path.exists():
            comp_path.mkdir()
        self.create_file(comp_path.joinpath(comp_path.joinpath(file_name + '.py')),py_file)