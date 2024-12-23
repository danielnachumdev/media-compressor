from pathlib import Path
import re
import shutil
import sys
import os
import subprocess
from enum import Enum
from typing import List, Literal, Optional

failed_imports: List[str] = []
try:
    import ffmpeg
except ImportError:
    failed_imports.append("ffmpeg-python")
try:
    from tqdm import tqdm
except ImportError:
    failed_imports.append("tqdm")
try:
    from PIL import Image
except ImportError:
    failed_imports.append("Pillow")
try:
    from fire import Fire
except ImportError:
    failed_imports.append("fire")
try:
    import rawpy
except ImportError:
    failed_imports.append("rawpy")

if failed_imports:
    print("Failed importing dependencies, please try re-installing them using the following command and then try again:")
    print(f"\t{sys.executable} -m pip install", *failed_imports)
    exit()


class FFMPEGCompressionPreset(Enum):
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"
    PLACEBO = "placebo"

    @classmethod
    def from_string(cls, s: str) -> 'FFMPEGCompressionPreset':
        for p in FFMPEGCompressionPreset:
            if p.value == s:
                return p
        raise ValueError


class ImageCompressionPreset(Enum):
    LOW = "low"


class Compressor:
    def _is_folder(self, s: str) -> bool:
        return os.path.splitext(s)[1] == ''

    def compress(self, input: str, output: str, preset: str, overwrite_existing: bool = True) -> None:
        input = str(Path(input).resolve().absolute()).replace("\\", "/")
        output = str(Path(output).resolve().absolute()).replace("\\", "/")
        if not self._is_folder(input):
            if self._is_folder(output):
                print("'input' is a file while 'output' is a folder. Aborting.")
                exit()
            self._compress_file(input, output, preset, overwrite_existing)
        else:
            if not self._is_folder(output):
                print("'input' is a folder while 'output' is a file. Aborting.")
                exit()
            self._compress_folder(input, output, preset, overwrite_existing)

    def _compress_folder(self, input: str, output: str, preset: str, overwrite_existing: bool = False) -> None:
        APPROVED_EXTENSIONS = {
            ".mp4", ".avi", ".mov", ".mkv", ".jpg", ".jpeg", ".png", ".tiff", ".cr2"
        }
        if overwrite_existing:
            if os.path.exists(output):
                shutil.rmtree(output)
        os.makedirs(output, exist_ok=True)
        for parentdir, subdirs, files in os.walk(input):
            files = list(filter(lambda f: os.path.splitext(f)
                         [1] in APPROVED_EXTENSIONS, files))
            if files:
                for file in (pbar := tqdm(files, total=len(files), position=0, desc=f"Files in {input}")):
                    name, ext = os.path.splitext(file)
                    file_input = os.path.join(input, file)
                    file_output = os.path.join(
                        output, f"{name} - COMPRESSED{ext}")
                    if os.path.exists(file_output) and not overwrite_existing:
                        continue
                    self._compress_file(file_input, file_output,
                                        preset, overwrite_existing, pbar)
            else:
                print(
                    "No applicable files found. try files with the following extensions:", APPROVED_EXTENSIONS)
            break

    def _compress_file(self, input: str, output: str, preset: str, overwrite_existing: bool = False, prev_pbar: Optional[tqdm] = None) -> None:
        """
        Determines the file type (video or image) and compresses accordingly.

        :param input: Input file path.
        :param output: Output file path.
        :param preset: Compression preset for video/image compression.
        :param overwrite_existing: Whether to overwrite an existing output file.
        """
        input = str(Path(input).resolve().absolute()).replace("\\", "/")
        output = str(Path(output).resolve().absolute()).replace("\\", "/")

        if os.path.exists(output):
            if overwrite_existing:
                os.remove(output)
            else:
                print(
                    f"'{output}' already exists. aborting. try adding 'overwrite_existing=True'")
                exit()

        _, ext = os.path.splitext(input)
        ext = ext.lower()

        if ext in [".mp4", ".avi", ".mov", ".mkv"]:  # Common video extensions
            # Compress video
            self._compress_video_with_progress(
                input, output, FFMPEGCompressionPreset.from_string(preset), prev_pbar)
        elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".cr2"]:  # Common image extensions
            # Compress image (losslessly or lossy)
            self._compress_image(
                input, output, FFMPEGCompressionPreset.from_string(preset), prev_pbar)
        else:
            print(f"Unsupported file format: {ext}")

    def _compress_video_with_progress(self, input_path: str, output_path: str, preset: FFMPEGCompressionPreset, prev_pbar: Optional[tqdm] = None):
        """
        Compresses a video using ffmpeg-python and displays a progress bar.

        :param input_path: Path to the input video file.
        :param output_path: Path to save the compressed video.
        :param preset: FFmpeg preset to balance speed and compression efficiency.
        """

        log = print
        if prev_pbar:
            log = prev_pbar.write

        try:
            # Get video duration in seconds
            probe = ffmpeg.probe(input_path)
            duration_in_seconds = float(probe['format']['duration'])
            filename = probe["format"]["filename"]
            # Build FFmpeg command
            command: List[str] = (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    vcodec="libx264",
                    crf=18,
                    preset=preset.value,
                    acodec="aac",
                    audio_bitrate="128k",
                    threads=os.cpu_count()
                )
                .compile()
            )
            # Run FFmpeg with progress monitoring
            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, universal_newlines=True)

            with tqdm(total=duration_in_seconds, unit="s", desc=f"Compressing {filename}", position=1 if prev_pbar else 0) as pbar:
                for line in process.stderr:
                    # Extract time from FFmpeg stderr
                    match = re.search(r"time=(\d+:\d+:\d+.\d+)", line)
                    if match:
                        time_str = match.group(1)
                        h, m, s = map(float, time_str.split(':'))
                        current_time = h * 3600 + m * 60 + s
                        pbar.n = int(current_time)
                        pbar.refresh()
                process.wait()
                if process.returncode == 0:
                    pbar.n = pbar.total
                    pbar.refresh()
                    log(
                        f"Video compressed successfully and saved to: {output_path}")
                else:
                    pbar.leave = False
                    cmd = " ".join(command)
                    log(
                        f"[ERROR] Failed processing {input_path}. Try running manually with:\n\t{cmd}")
        except ffmpeg.Error as e:
            log(f"Error during compression: {e.stderr.decode()}")

        except Exception as e:
            log(f"An error occurred: {e}")

    def _compress_image(self, input_path: str, output_path: str, preset: FFMPEGCompressionPreset, pbar_pos: int = 0):
        """
        Compresses an image losslessly or lossy using ffmpeg, Pillow (based on the file type), or rawpy (for CR2 files).

        :param input_path: Path to the input image file.
        :param output_path: Path to save the compressed image.
        :param preset: Compression preset for image compression.
        """
        pass


__all__ = [
    "Compressor"
]
if __name__ == "__main__":
    Fire(Compressor().compress)
