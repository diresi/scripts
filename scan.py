#!/home/resi/opt/virtualenvs/sane/bin/python
import sys
import os
import logging
import tempfile
import subprocess
import pyinsane.abstract as pyinsane
import PyPDF2 as pypdf
import PIL.Image

DPI = 300
TARGET_DPI = 75

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

def spawnDaemon(func):
    # do the UNIX double-fork magic, see Stevens' "Advanced
    # Programming in the UNIX Environment" for details (ISBN 0201563177)
    try:
        pid = os.fork()
        if pid > 0:
            # parent process, return and keep running
            return
    except OSError as e:
        log.exception("fork #1 failed: %d (%s)" % (e.errno, e.strerror))
        sys.exit(1)

    os.setsid()

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        log.exception("fork #2 failed: %d (%s)" % (e.errno, e.strerror))
        sys.exit(1)

    # do stuff
    func()

    # all done
    os._exit(os.EX_OK)

def open_file(fn):
    subprocess.Popen(["gvfs-open", fn])

def decode(data):
    if isinstance(data, (list, tuple)):
        return [decode(d) for d in data]
    if isinstance(data, bytes):
        return data.decode()
    return str(data)

def find_in_str_ic(ls, pat):
    try:
        return [s for s in ls if pat.lower() in s.lower()][0]
    except IndexError:
        return None

def find_devices():
    devices = pyinsane.get_devices()
    return devices

def open_device(device):
    if device.startswith("#"):
        dev = find_devices()[int(device[1:])]
    else:
        dev = pyinsane.Scanner(device)
    return dev

def find_sources(dev):
    return decode(dev.options["source"].constraint)

def find_resolutions(dev):
    return decode(dev.options["resolution"].constraint)

def wait_for_key(hint="Press enter to continue\n"):
    return input(hint)

def scan_n_pages(dev, num_pages=0, duplex=False, resolution=DPI):
    num_pages = max(num_pages, 0)
    sources = find_sources(dev)

    # Note:
    # It is _very_ important to set the "source" option before (any)
    # "resolution" option. Setting the source seems to reset the resolution to
    # the device default value.
    # Taken from https://bugs.launchpad.net/simple-scan/+bug/891586/comments/25
    def update_options(source=None):
        if source:
            dev.options["source"].value = source
        dev.options["color"] = "Color"
        dev.options["adf-mode"].value = "Duplex" if duplex else "Simplex"
        dev.options["scan-area"].value = "A4"
        dev.options["resolution"].value = resolution
        return dev.options["resolution"].value

    # update once to determine the next matching resolution
    resolution = update_options()
    log.debug("using resolution %s dpi" % (resolution,))

    try:
        log.debug("trying ADF")

        is_adf = True
        update_options(find_in_str_ic(sources, "feed"))
        scan_session = pyinsane.ScanSession(pyinsane.MultipleScan(dev))
    except StopIteration:
        log.debug("ADF empty")

        is_adf = False
        update_options(find_in_str_ic(sources, "flat"))
        scan_session = pyinsane.ScanSession(pyinsane.MultipleScan(dev))

        if not num_pages:
            num_pages = 1

    page_count = 0
    while True:
        try:
            try:
                scan_session.scan.read()
            except EOFError:
                page_count += 1

                if is_adf and duplex and not (page_count % 2):
                    scan_session.images[-1] = scan_session.images[-1].rotate(180)

                if page_count == num_pages:
                    raise StopIteration

                if not is_adf:
                    wait_for_key()

        except StopIteration:
            break

    log.debug("read %s pages" % (page_count,))
    return scan_session.images, resolution

def scale_image(im, current_resolution, target_resolution=TARGET_DPI):
    f = target_resolution / current_resolution
    w, h = im.size
    return im.resize((int(w * f), int(h * f)), PIL.Image.ANTIALIAS)

def make_pdf(fn, images, resolution=DPI):
    if not images:
        return

    outfile = open(fn, "wb")

    if len(images) == 1:
        images[0].save(outfile, "PDF", resolution=resolution)
    else:
        pdf_out = pypdf.PdfFileWriter()
        for image in images:
            tfo = tempfile.TemporaryFile()
            image.save(tfo, "PDF", resolution=resolution)
            pdf_in = pypdf.PdfFileReader(tfo)
            for i in range(pdf_in.numPages):
                pdf_out.addPage(pdf_in.getPage(i))
        pdf_out.write(outfile)

def argparse():
    import argparse
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-L", "--list-devices", action="store_true",
                        help="find availabe devices")
    parser.add_argument("-n", "--num-pages", default=0, type=int,
                        help="number of pages to scan (automatic if 0)")
    parser.add_argument("-D", "--device", default="#0",
                        help="device number (#<num>) or identification to use")
    parser.add_argument("-S", "--show-sources", action="store_true",
                        help="show available sources for the current device")
    parser.add_argument("-s", "--source", default="auto",
                        help="use specified source (auto, any entry from --show-sources)")
    parser.add_argument("-d", "--duplex", action="store_true",
                        help="use duplex mode")
    parser.add_argument("--dpi", default=DPI, type=int,
                        help="scanner resolution")
    parser.add_argument("--target-dpi", default=TARGET_DPI, type=int,
                        help="output resolution")
    parser.add_argument("-R", "--show-resolutions", action="store_true",
                        help="show available resolutions for the current device")
    parser.add_argument("-v", "--view", action="store_true",
                        help="show document after scanning (using gvfs-open)")
    parser.add_argument("-f", "--force", action="store_true",
                        help="force overwriting of existing files")
    parser.add_argument("outfile", metavar="OUTFILE", nargs="?", default="scan.pdf",
                        help="name of output file")

    return parser.parse_args()

def cli_main(args):
    if args.list_devices:
        devs = find_devices()
        print("Found %s devices:" % (len(devs),))
        for i, dev in enumerate(devs):
            print("#%s: %s" % (i, dev.name))
        return

    if os.path.exists(args.outfile) and not args.force:
        raise Exception("File exists: %s\nUse --force to overwrite." % args.outfile)

    dev = open_device(args.device)
    log.debug("Using device '%s'" % (dev.name,))

    if args.show_sources:
        sources = find_sources(dev)
        print("Available sources:", ", ".join(sources))
        return

    if args.show_resolutions:
        resolutions = find_resolutions(dev)
        print("Available resolutions:", ", ".join(resolutions))
        return

    images, resolution = scan_n_pages(dev, args.num_pages, args.duplex, args.dpi)
    images = [scale_image(im, resolution, args.target_dpi) for im in images]
    make_pdf(args.outfile, images, args.target_dpi)

    if args.view:
        spawnDaemon(lambda: open_file(args.outfile))

    return args.outfile

if __name__ == "__main__":
    cli_main(argparse())
