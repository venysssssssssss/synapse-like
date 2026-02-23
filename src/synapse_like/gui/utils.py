from evdev import ecodes


def event_code_name(code: int) -> str:
    if code in ecodes.KEY:
        return ecodes.KEY[code]
    for name, value in ecodes.ecodes.items():
        if value == code:
            return name
    return str(code)
