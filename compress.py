import math
import re
import shutil
import sys
import os
import subprocess
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, Hashable, Iterable, List, Literal, Optional, Set, Tuple

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


class Compressor(ABC):

    @abstractmethod
    def compress(self, src: str, dst: str, preset: str, *,
                 overwrite: bool = False, cpu_utilization: float = 0.8, **kwargs) -> None: ...


class FolderCompressor(Compressor):
    def __init__(self, file_compressor: 'FileCompressor'):
        self.file_compressor = file_compressor

    def compress(self, src: str, dst: str, preset: str, *,
                 overwrite: bool = False, utilization: float = 0.8) -> None:
        APPROVED_EXTENSIONS = {
            ".mp4", ".avi", ".mov", ".mkv", ".jpg", ".jpeg", ".png", ".tiff", ".cr2"
        }
        if overwrite:
            if os.path.exists(dst):
                shutil.rmtree(dst)
        os.makedirs(dst, exist_ok=True)
        for parentdir, subdirs, files in os.walk(src):
            files = list(filter(lambda f: os.path.splitext(f)
                         [1] in APPROVED_EXTENSIONS, files))
            break
        if not files:
            print(
                "No applicable files found. try files with the following extensions:", APPROVED_EXTENSIONS)
            exit()
        for file in (pbar := tqdm(files, total=len(files), position=0, desc=f"Files in {src}")):
            name, ext = os.path.splitext(file)
            updated_src = os.path.join(src, file)
            updated_dst = os.path.join(dst, f"{name}{ext}")
            if os.path.exists(dst) and not overwrite:
                continue
            self.file_compressor.compress(updated_src, updated_dst,
                                          preset, overwrite=overwrite, prev_pbar=pbar, utilization=utilization)


class FileCompressor(Compressor):
    @abstractmethod
    def compress(self, src, dst, preset, *, overwrite=False,
                 prev_pbar: Optional[tqdm] = None, utilization=0.8): ...


class SwitchCompressor(FileCompressor):
    def __init__(self, mapping: Dict[Tuple[str, ...], FileCompressor], default: Optional[FileCompressor] = None):
        self.mapping = mapping
        self.default = default

    def compress(self, src: str, *args, **kwargs):
        _, ext = os.path.splitext(src)
        all_extensions = set()
        for extensions, compressor in self.mapping.items():
            all_extensions.update(extensions)
            if ext in extensions:
                compressor.compress(src, *args, **kwargs)
                break
        else:
            if not self.default:
                print(f"Invalid extension '{ext}' not in {all_extensions}")
            else:
                self.default.compress(src, *args, **kwargs)


class ObjectCompressor(Compressor):
    def __init__(self, file_compressor: 'FileCompressor'):
        self.folder_compressor = FolderCompressor(file_compressor)
        self.file_compressor = file_compressor

    def _is_folder(self, s: str) -> bool:
        return os.path.splitext(s)[1] == ''

    def compress(self, src: str, dst: str, preset: str, *,
                 overwrite: bool = False, utilization: float = 0.8):
        utilization = max(0.1, min(utilization, 1.0))
        src = str(Path(src).resolve().absolute())
        dst = str(Path(dst).resolve().absolute())
        explorer_target = dst
        if not self._is_folder(src):
            if self._is_folder(dst):
                print(
                    "'src' is a file while 'dst' is a folder. Aborting.")
                exit()
            explorer_target = str(Path(dst).resolve().absolute().parent)
            self.file_compressor.compress(
                src, dst, preset, overwrite=overwrite, utilization=utilization)
        else:
            if not self._is_folder(dst):
                print(
                    "'src' is a folder while 'dst' is a file. Aborting.")
                exit()
            self.folder_compressor.compress(
                src, dst, FFMPEGCompressionPreset.from_string(preset), overwrite=overwrite, utilization=utilization)

        cmd = "open"
        if sys.platform == "win32":
            cmd = "start"
        os.system(f"{cmd} {explorer_target}")


class VideoCompressor(FileCompressor):
    ...


class ImageCompressor(FileCompressor):
    ...


class FFMPEGImageCompressor(ImageCompressor):
    def compress(self, src: str, dst: str, preset: FFMPEGCompressionPreset, *, overwrite: bool = False, prev_pbar: Optional[tqdm] = None, utilization: float = 1.0):
        """
        Compresses an image losslessly or lossy using ffmpeg, Pillow (based on the file type), or rawpy (for CR2 files).

        :param input_path: Path to the input image file.
        :param output_path: Path to save the compressed image.
        :param preset: Compression preset for image compression.
        """
        input_ext = os.path.splitext(src)[1].lower()
        extra_kwargs = []
        if input_ext in [".jpg", ".jpeg"]:
            extra_kwargs = {"qscale:v": "2"}  # Adjust quality for JPEG
        elif input_ext == ".png":
            # Adjust compression level for PNG
            extra_kwargs = {"compression_level": "10"}
        command: List[str] = (
            ffmpeg
            .input(src)
            .output(
                dst,
                preset=preset.value,
                threads=max(1, math.floor(os.cpu_count()*utilization)),
                **extra_kwargs
            )
            .compile()
        )
        # Run FFmpeg with progress monitoring
        process = subprocess.Popen(
            command, stderr=subprocess.PIPE, universal_newlines=True)
        process.wait()


class FFMPEGVideoCompressor(VideoCompressor):
    def compress(self, src: str, dst: str, preset: FFMPEGCompressionPreset, *, prev_pbar: Optional[tqdm] = None, cpu_utilization: float = 1.0):
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
            probe = ffmpeg.probe(src)
            duration_in_seconds = float(probe['format']['duration'])
            filename = probe["format"]["filename"]
            # Build FFmpeg command
            command: List[str] = (
                ffmpeg
                .input(src)
                .output(
                    dst,
                    vcodec="libx264",
                    crf=23,
                    preset=preset.value,
                    acodec="aac",
                    audio_bitrate="128k",
                    threads=max(1, math.floor(os.cpu_count()*cpu_utilization))
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
                        f"Video compressed successfully and saved to: {dst}")
                else:
                    pbar.leave = False
                    cmd = " ".join(command)
                    log(
                        f"[ERROR] Failed processing {src}. Try running manually with:\n\t{cmd}")
        except ffmpeg.Error as e:
            log(f"Error during compression: {e.stderr.decode()}")

        except Exception as e:
            log(f"An error occurred: {e}")


class Main(ObjectCompressor):
    def __init__(self):
        super().__init__(SwitchCompressor({
            tuple([".mp4", ".avi", ".mov", ".mkv"]): FFMPEGVideoCompressor(),
            tuple([".jpg", ".jpeg", ".png", ".tiff", ".cr2"]): FFMPEGImageCompressor()
        }))


if __name__ == "__main__":
    Fire(Main().compress)
