from app.ports.crm import ICRMPort, CRMLead
from app.ports.email_parser import IEmailParserPort, ParsedLead
from app.ports.workflow import IWorkflowPort

__all__ = [
    "ICRMPort",
    "CRMLead",
    "IEmailParserPort",
    "ParsedLead",
    "IWorkflowPort",
]
