from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Set

class PageSelectionMode(Enum):
    ALL = "All Pages"
    RANGE = "Page Range"
    SPECIFIC = "Specific Pages"

@dataclass
class PageSelection:
    mode: PageSelectionMode = PageSelectionMode.ALL
    range_from: int = 1
    range_to: int = 1
    specific_input: str = ""

    def validate(self, total_pages: int) -> Tuple[bool, str]:
        if total_pages <= 0:
            return False, "Total PDF page count must be greater than 0."

        if self.mode == PageSelectionMode.ALL:
            return True, ""

        elif self.mode == PageSelectionMode.RANGE:
            if self.range_from < 1:
                return False, f"Start page ({self.range_from}) must be at least 1."
            if self.range_to < 1:
                return False, f"End page ({self.range_to}) must be at least 1."
            if self.range_from > total_pages:
                return False, f"Start page ({self.range_from}) exceeds total pages ({total_pages})."
            if self.range_to > total_pages:
                return False, f"End page ({self.range_to}) exceeds total pages ({total_pages})."
            if self.range_from > self.range_to:
                return False, f"Invalid range: 'From' page ({self.range_from}) cannot be greater than 'To' page ({self.range_to})."
            return True, ""

        elif self.mode == PageSelectionMode.SPECIFIC:
            raw = self.specific_input.strip()
            if not raw:
                return False, "Specific pages input cannot be empty."

            items = [p.strip() for p in raw.split(",")]
            for item in items:
                if not item:
                    return False, "Malformed page selection: empty item between commas."
                if "-" in item:
                    sub = item.split("-")
                    if len(sub) != 2 or not sub[0].isdigit() or not sub[1].isdigit():
                        return False, f"Malformed page range '{item}'."
                    start_p, end_p = int(sub[0]), int(sub[1])
                    if start_p < 1:
                        return False, f"Page number ({start_p}) in range '{item}' must be at least 1."
                    if end_p < 1:
                        return False, f"Page number ({end_p}) in range '{item}' must be at least 1."
                    if start_p > total_pages:
                        return False, f"Page number ({start_p}) in range '{item}' exceeds total pages ({total_pages})."
                    if end_p > total_pages:
                        return False, f"Page number ({end_p}) in range '{item}' exceeds total pages ({total_pages})."
                    if start_p > end_p:
                        return False, f"Invalid range '{item}': start page ({start_p}) is greater than end page ({end_p})."
                else:
                    if not item.isdigit():
                        return False, f"Invalid page number '{item}'."
                    p_num = int(item)
                    if p_num < 1:
                        return False, f"Page number ({p_num}) must be at least 1."
                    if p_num > total_pages:
                        return False, f"Page number ({p_num}) exceeds total pages ({total_pages})."
            return True, ""

        return False, "Unknown selection mode."

    def get_selected_pages(self, total_pages: int) -> List[int]:
        is_valid, _ = self.validate(total_pages)
        if not is_valid:
            return []

        if self.mode == PageSelectionMode.ALL:
            return list(range(1, total_pages + 1))

        elif self.mode == PageSelectionMode.RANGE:
            return list(range(self.range_from, self.range_to + 1))

        elif self.mode == PageSelectionMode.SPECIFIC:
            selected_set: Set[int] = set()
            items = [p.strip() for p in self.specific_input.strip().split(",")]
            for item in items:
                if "-" in item:
                    sub = item.split("-")
                    start_p, end_p = int(sub[0]), int(sub[1])
                    for p in range(start_p, end_p + 1):
                        selected_set.add(p)
                else:
                    selected_set.add(int(item))
            return sorted(list(selected_set))

        return []
