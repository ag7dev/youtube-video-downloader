import yt_dlp as youtube_dl
import os
import sys
import time
import threading
from itertools import cycle
from colorama import Fore, Back, Style, init
from shutil import which

# Initialize colorama for cross-platform color support
init(autoreset=True)

# --------------------------
# Constants and Configuration
# --------------------------
DEFAULT_DOWNLOAD_DIR = os.path.join(os.environ['USERPROFILE'], 'Desktop')
FFMPEG_MSG = f"""
{Back.RED}{Fore.WHITE} FFMPEG REQUIRED {Style.RESET_ALL}
{Fore.YELLOW}Please install FFmpeg for audio conversions:
1. Download from {Fore.CYAN}https://ffmpeg.org/
2. Add to system PATH
3. Restart this program

------------
Or use the following command:
> winget install ffmpeg
--> And then restart this program

"""

# --------------------------
# Animation Utilities
# --------------------------
class Spinner:
    def __init__(self):
        self.spinner = cycle(['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'])
        self.running = False
        self.thread = None

    def spin(self, message):
        self.running = True
        sys.stdout.write("\033[?25l")  # Hide cursor
        while self.running:
            sys.stdout.write(f"\r{Fore.BLUE}{next(self.spinner)}{Style.RESET_ALL} {message}...  ")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\033[K")  # Clear line
        sys.stdout.write("\033[?25h")  # Show cursor

    def start(self, message):
        self.thread = threading.Thread(target=self.spin, args=(message,))
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# --------------------------
# Core Downloader Class
# --------------------------
class YoutubeDownloader:
    def __init__(self):
        self.download_dir = DEFAULT_DOWNLOAD_DIR
        self.ydl_opts = {
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'noplaylist': True,
        }
        self.spinner = Spinner()
        self.current_status = {}
        self.downloaded_filename = None

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            self.current_status = d
        elif d['status'] == 'finished':
            self.spinner.stop()
            self.downloaded_filename = d.get('filename')
            print(f"\r{Fore.GREEN}✓ Processing complete{Style.RESET_ALL}")

    def _validate_ffmpeg(self):
        if not which('ffmpeg'):
            print(FFMPEG_MSG)
            sys.exit(1)

    def _display_header(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        header = f"""
{Fore.BLUE}╭──────────────────────────────────────────╮
{Fore.BLUE}│{Fore.CYAN}          🎬 YOUTUBE DOWNLOADER 🎵         {Fore.BLUE}│
{Fore.BLUE}╰──────────────────────────────────────────╯{Style.RESET_ALL}
        """
        print(header)
        print(f"{Fore.LIGHTBLACK_EX}  Platform: {sys.platform} | Python: {sys.version.split()[0]}{Style.RESET_ALL}\n")

    def _set_download_dir(self):
        self._display_header()
        print(f"{Fore.YELLOW}Current download directory:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{self.download_dir}{Style.RESET_ALL}")
        change = input(f"\n{Fore.YELLOW}Change directory? (y/n):{Style.RESET_ALL} ").lower()
        
        if change == 'y':
            new_dir = input(f"\n{Fore.YELLOW}Enter new path:{Style.RESET_ALL} ").strip()
            if os.path.isdir(new_dir):
                self.download_dir = new_dir
                self.ydl_opts['outtmpl'] = os.path.join(self.download_dir, '%(title)s.%(ext)s')
                print(f"\n{Fore.GREEN}✓ Directory updated{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}⚠ Directory not found! Using default{Style.RESET_ALL}")
            time.sleep(1)

    def _get_choice(self, prompt, options):
        while True:
            self._display_header()
            print(f"{Fore.YELLOW}{prompt}{Style.RESET_ALL}")
            for i, (emoji, text) in enumerate(options, 1):
                print(f"  {Fore.YELLOW}{i}) {emoji} {text}{Style.RESET_ALL}")
            
            try:
                choice = input(f"\n{Fore.YELLOW}Enter choice (1-{len(options)}):{Style.RESET_ALL} ")
                if 1 <= int(choice) <= len(options):
                    return choice
                raise ValueError
            except (ValueError, KeyError):
                print(f"\n{Back.RED}{Fore.WHITE} ERROR {Style.RESET_ALL} Invalid choice!")
                time.sleep(1)

    def _get_url(self):
        self._display_header()
        return input(f"{Fore.YELLOW}🎯 Enter video URL:{Style.RESET_ALL} ").strip()

    def _confirm_download(self, info):
        self._display_header()
        print(f"{Fore.YELLOW}📄 Video Details:{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}▸ Title: {info.get('title', 'N/A')}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}▸ Duration: {info.get('duration_string', 'N/A')}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}▸ Channel: {info.get('uploader', 'N/A')}{Style.RESET_ALL}")
        
        if filesize := info.get('filesize') or info.get('filesize_approx'):
            size_mb = filesize / (1024 * 1024)
            print(f"  {Fore.CYAN}▸ Size: {size_mb:.1f} MB{Style.RESET_ALL}")
        
        return input(f"\n{Fore.YELLOW}🚀 Start download? (y/n):{Style.RESET_ALL} ").lower() == 'y'

    def _set_format(self, choice):
        format_options = {
            '1': {'format': 'bestaudio/best', 'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'}]},
            '2': {'format': 'bestaudio/best'},
            '3': {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'},
            '4': {'format': 'bestvideo+bestaudio/best'}
        }
        self.ydl_opts.update(format_options[choice])

    def download(self):
        try:
            self._validate_ffmpeg()
            self._display_header()
            self._set_download_dir()

            format_options = [
                ("🎵", "MP3 Audio (High Quality)"),
                ("🎵", "WEBM Audio (Original Quality)"),
                ("📹", "MP4 Video+Audio (Recommended)"),
                ("📹", "WEBM Video+Audio (Best Quality)")
            ]
            choice = self._get_choice("📦 Select download format:", format_options)
            self._set_format(choice)

            url = self._get_url()

            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not self._confirm_download(info):
                print(f"\n{Fore.YELLOW}🚫 Download canceled{Style.RESET_ALL}")
                return

            self.spinner.start("Downloading")
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([url])

            print(f"\n{Fore.GREEN}✓ Download successful!{Style.RESET_ALL}")
            if self.downloaded_filename:
                print(f"{Fore.CYAN}▶ File saved to:{Style.RESET_ALL}")
                print(f"{Fore.LIGHTBLACK_EX}{self.downloaded_filename}{Style.RESET_ALL}")

        except youtube_dl.DownloadError as e:
            self.spinner.stop()
            print(f"\n{Back.RED}{Fore.WHITE} ERROR {Style.RESET_ALL} {str(e)}")
        except KeyboardInterrupt:
            self.spinner.stop()
            print(f"\n{Fore.YELLOW}⚠ Operation canceled{Style.RESET_ALL}")
        except Exception as e:
            self.spinner.stop()
            print(f"\n{Back.RED}{Fore.WHITE} UNEXPECTED ERROR {Style.RESET_ALL} {str(e)}")
        finally:
            input(f"\n{Fore.LIGHTBLACK_EX}👋 Press Enter to exit...{Style.RESET_ALL}")

# --------------------------
# Main Execution
# --------------------------
if __name__ == "__main__":
    downloader = YoutubeDownloader()
    downloader.download()
