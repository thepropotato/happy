"""WHAT EACH SYSTEM CALLS A THING, AND WHAT A PERSON CALLS IT."""

MAC_KINDS = {
    "AXButton": "button",
    "AXCheckBox": "checkbox",
    "AXRadioButton": "radio button",
    "AXTextField": "text field",
    "AXTextArea": "text box",
    "AXStaticText": "text",
    "AXLink": "link",
    "AXMenuBarItem": "menu",
    "AXMenuItem": "menu item",
    "AXPopUpButton": "dropdown",
    "AXComboBox": "dropdown",
    "AXTabGroup": "tabs",
    "AXSlider": "slider",
    "AXImage": "image",
    "AXWindow": "window",
    "AXToolbar": "toolbar",
    "AXRow": "row",
    "AXCell": "cell",
    "AXDisclosureTriangle": "expander",
}

WINDOWS_KINDS = {
    50000: "button",
    50002: "checkbox",
    50003: "dropdown",
    50004: "text field",
    50005: "link",
    50006: "image",
    50007: "list item",
    50011: "menu item",
    50013: "radio button",
    50015: "slider",
    50019: "tab",
    50020: "text",
    50021: "toolbar",
    50024: "row",
    50032: "window",
}

# THE ONES WHOSE VALUE IS A TICK RATHER THAN SOMETHING TO READ OUT.
MAC_TICKABLE = ("AXCheckBox", "AXRadioButton", "AXDisclosureTriangle")

# A CLOSED MENU KEEPS ITS WHOLE SUBTREE, INVISIBLE AND UNCLICKABLE.
MAC_FOLDED = ("AXMenu", "AXMenuBar")

# CHARACTERS THAT DECIDE WHICH WAY TEXT RUNS AND DRAW NOTHING.
MARKS = dict.fromkeys(
    [0x200B, 0x200E, 0x200F, 0xFEFF]
    + list(range(0x202A, 0x202F))
    + list(range(0x2066, 0x206A))
)


def plain(role):
    """A ROLE NOBODY MAPPED, AS SOMETHING READABLE. AXScrollBar IS A SCROLL BAR."""
    bare = role.removeprefix("AX")
    spaced = "".join(f" {letter}" if letter.isupper() else letter for letter in bare)

    return spaced.strip().lower()


def wording(value):
    """AN ATTRIBUTE AS A SHORT STRING, WHATEVER THE SYSTEM HANDED BACK."""
    if value is None or isinstance(value, bool):
        return ""

    said = str(value).translate(MARKS).strip()

    return said if said and said != "None" else ""
