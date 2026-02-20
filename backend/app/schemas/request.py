from pydantic import BaseModel, ConfigDict
from app.schemas.enums import CompTemplate, FormatOutPut


class ExampleRequest(BaseModel):
    example_id: str
    source: str


class Problem(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    task_id: str
    ques_all: str = ""
    comp_template: CompTemplate = CompTemplate.CHINA
    format_output: FormatOutPut = FormatOutPut.Markdown
