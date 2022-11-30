"""This module adds tools to convert images, time and other things like that.
"""

import datetime

from cairosvg import svg2png

__all__ = [
    "convert_svg_to_png",
    "convert_timedelta",
]

def convert_svg_to_png(
    svg_uri_path: str,
    png_output_path: str
):
    """This function converts a SVG image into a png.
    
    The input SVG file can be a local file or a remote location.
    """
    svg2png(
        url=svg_uri_path,
        write_to=png_output_path,
    )

def convert_timedelta(time: datetime.timedelta) -> str:
    """Converts timedelta in a nice string representation."""
    if time.days < 3:
        return f"{int(time.total_seconds ()// 3600)} hours"
    else:
        days = time.total_seconds() // 3600 // 24
        hours = time.total_seconds() // 3600 - days * 24
        return f"{int(days)} days and {int(hours)} hours"

if __name__ == "__main__":
    convert_svg_to_png("https://cdn.wynncraft.com/nextgen/classes/icons/archer.svg", "./archer.png")
    convert_svg_to_png("https://cdn.wynncraft.com/nextgen/classes/icons/mage.svg", "./mage.png")
    convert_svg_to_png("https://cdn.wynncraft.com/nextgen/classes/icons/shaman.svg", "./shaman.png")