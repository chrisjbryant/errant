from typing import Tuple, Optional


class ErrorType:

    #Operations
    UNKNOWN_OP = ""
    MISSING_OP = "M"
    UNECESSARY_OP = "U"
    REPLACEMENT_OP = "R"

    def __init__(self, 
                 operation: str,
                 category: Optional[str] = None,
                 sub_category: Optional[str] = None):
        
        self.operation = operation
        self.category = category
        self.sub_category = sub_category
    
    @staticmethod
    def from_string(text: str) -> 'errant.edit.ErrorType':
        data = text.split(':')
        if len(data) == 1:
            return ErrorType(ErrorType.UNKNOWN_OP, data[0])
        elif len(data) == 2:
            return ErrorType(data[0], data[1])
        else:
            return ErrorType(data[0], data[1], data[2])

    def __repr__(self) -> str:
        representation = ""
        if self.operation:
            representation += self.operation + ":"
        if self.category:
            representation += self.category
            if self.sub_category:
                representation += ":" + self.sub_category
        return representation

class Edit:

    def __init__(self,
                 original_span: Tuple[int, int],
                 corrected_span: Tuple[int, int],
                 edit_text: str, 
                 error_type: Optional[ErrorType] = None):
        self.original_span = original_span
        self.corrected_span = corrected_span
        self.edit_text = edit_text
        self.error_type = error_type

    def __repr__(self):
        return f'original:{self.original_span} corrected:{self.corrected_span}'\
               f' edit:{self.edit_text} error_type:{self.error_type}'