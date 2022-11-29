"""This module adds tools to convert images, time and other things like that.
"""

from cairosvg import svg2png

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
