import os
import glob
import time
import pathlib

import click
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.shortcuts import ProgressBar

import pint
import Lima.Core
import Lima.Eiger
from Lima.Core import AcqRunning, AcqFault, FrameDim


ur = pint.UnitRegistry()


ErrorMap = {
    Lima.Core.CtControl.NoError:           "No error",
    Lima.Core.CtControl.SaveUnknownError:  "Saving error",
    Lima.Core.CtControl.SaveOpenError:     "Save file open error",
    Lima.Core.CtControl.SaveCloseError:    "Save file close error",
    Lima.Core.CtControl.SaveAccessError:   "Save access error",
    Lima.Core.CtControl.SaveOverwriteError: "Save overwrite error",
    Lima.Core.CtControl.SaveDiskFull:      "Save disk full",
    Lima.Core.CtControl.SaveOverun:        "Save overrun",
    Lima.Core.CtControl.ProcessingOverun:  "Soft Processing overrun",
    Lima.Core.CtControl.CameraError:       "Camera Error",
}


class ReportTask:
    DONE = '[<green>DONE</green>]'
    FAIL = '[<red>FAIL</red>]'
    STOP = '[<magenta><b>STOP</b></magenta>]'
    SKIP = '[<yellow>SKIP</yellow>]'

    def __init__(self, message, **kwargs):
        length = kwargs.pop('length', 40)
        template = '{{:.<{}}} '.format(length)
        self.message = template.format(message)
        kwargs.setdefault('end', '')
        kwargs.setdefault('flush', True)
        self.kwargs = kwargs
        self.skipped = False

    def __enter__(self):
        print_formatted_text(HTML(self.message), **self.kwargs)
        self.start = time.time()
        return self

    def skip(self):
        self.DONE = self.SKIP
        self.skipped = True

    @property
    def elapsed(self):
        return self.end - self.start

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.end = time.time()
        if exc_type is None:
            msg = self.DONE
            if not self.skipped:
                elapsed = ((self.elapsed) * ur.s).to_compact()
                msg += ' (took {:~.4})'.format(elapsed)
        elif exc_type is KeyboardInterrupt:
            return False
        else:
            msg = self.FAIL + f'({exc_value!r})'
        print_formatted_text(HTML(msg))
        return False


class AcquisitionContext(Lima.Core.CtControl.ImageStatusCallback):

    def __init__(self, ctrl, cb=None):
        super().__init__()
        self.ctrl = ctrl
        self.cb = cb

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type == KeyboardInterrupt:
            self.stopAcq()
        elif self.status.AcquisitionStatus == AcqRunning:
            self.stopAcq()

    def prepareAcq(self):
        self.ctrl.prepareAcq()

    def startAcq(self):
        self.ctrl.startAcq()

    def stopAcq(self):
        self.ctrl.stopAcq()

    @property
    def status(self):
        return self.ctrl.getStatus()


def configure(ctrl, options):
    th_mgr = Lima.Core.Processlib.PoolThreadMgr.get()
    th_mgr.setNumberOfThread(options.nb_processing_tasks)

    acq = ctrl.acquisition()
    saving = ctrl.saving()
    buff = ctrl.buffer()
    saving.setFormat(options.saving_format)
    saving.setPrefix(options.saving_prefix)
    saving.setSuffix(options.saving_suffix)
    saving.setMaxConcurrentWritingTask(options.nb_saving_tasks)
    if options.saving_directory:
        saving.setSavingMode(saving.AutoFrame)
        saving.setDirectory(options.saving_directory)
    acq.setAcqExpoTime(options.exposure_time)
    acq.setAcqNbFrames(options.nb_frames)
    buff.setMaxMemory(options.max_buffer_size)


def cleanup(ctrl, options):
    pattern = options.saving_prefix + '*' + options.saving_suffix
    pattern = pathlib.Path(options.saving_directory) / pattern
    for filename in glob.glob(str(pattern)):
        os.remove(filename)


def AcqProgBar(ctrl, options):
    iface = ctrl.hwInterface()
    info = iface.getHwCtrlObj(Lima.Core.HwCap.DetInfo)
    frame_dim = FrameDim(info.getDetectorImageSize(), info.getCurrImageType())
    exposure_time = options.exposure_time * ur.second
    acq_time = (options.nb_frames * exposure_time).to_compact()
    frame_rate = (1/exposure_time).to(ur.Hz).to_compact()
    title = f'Acquiring on {info.getDetectorModel()} ({info.getDetectorType()}) | ' \
            f'{options.nb_frames} x {exposure_time:~.4}({frame_rate:~.4}) = {acq_time:~.4}  | ' \
            f'{frame_dim}'
    return ProgressBar(
        title=title,
        bottom_toolbar=HTML(" <b>[Control-C]</b> abort")
    )


class AcquisitionMonitor:
    def __init__(self, ctx, prog_bar, options):
        self.ctx = ctx
        nb_frames = options.nb_frames
        self.prog_bar = prog_bar
        self.acq_counter = prog_bar(label='Acquired', total=nb_frames)
        self.base_counter = prog_bar(label='Base Ready', total=nb_frames)
        self.img_counter = prog_bar(label='Ready', total=nb_frames)
        if options.saving_directory:
            self.save_counter = prog_bar(label='Saved', total=nb_frames)
        else:
            self.save_counter = None

    def set_items_completed(self, bar, n):
        bar.items_completed = n
        self.prog_bar.invalidate()

    def update(self, status):
        counters = status.ImageCounters
        self.set_items_completed(self.acq_counter, counters.LastImageAcquired + 1)
        self.set_items_completed(self.base_counter, counters.LastBaseImageReady + 1)
        self.set_items_completed(self.img_counter, counters.LastImageReady + 1)
        if self.save_counter:
            self.set_items_completed(self.save_counter, counters.LastImageSaved + 1)
        acq = status.AcquisitionStatus
        if status.Error != Lima.Core.CtControl.NoError:
            error = ErrorMap[status.Error]
            print_formatted_text(HTML(f'<red>Acquisition error: </red> <b>{error}</b>'))
        elif acq == AcqFault:
            print_formatted_text(HTML(f'<orange>Acquisition fault</orange>'))
        return acq == AcqRunning and status.Error == Lima.Core.CtControl.NoError

    def run(self):
        while True:
            status = self.ctx.status
            if not self.update(status):
                break
            time.sleep(0.05)
        self.update(self.ctx.status)


def frame_type(text):
    return getattr(Lima.Core, text.capitalize())


def file_format(text):
    return getattr(Lima.Core.CtSaving, text)


@click.command("acquire")
@click.option('-n', '--nb-frames', default=10, type=int, show_default=True)
@click.option('-e', '--exposure-time', default=0.1, type=float, show_default=True)
@click.option('-l', '--latency-time', default=0.0, type=float, show_default=True)
@click.option('-d', '--saving-directory', default=None, type=str, show_default=True)
@click.option(
    '-f', '--saving-format', default='EDF',
    type=file_format, help='saving format', show_default=True)
@click.option('-p', '--saving-prefix', default='image_', type=str, show_default=True)
@click.option('-s', '--saving-suffix', default='__AUTO_SUFFIX__', type=str, show_default=True)
@click.option(
    '--frame-type', type=frame_type, default='Bpp16', show_default=True,
    help='pixel format (ex: Bpp8) [default: Bpp16]')
@click.option('--max-buffer-size', type=float, default=50, show_default=True,
              help='maximum buffer size (% total memory)')
@click.option('--nb-saving-tasks', type=int, default=1, show_default=True,
              help='nb. of saving tasks')
@click.option('--nb-processing-tasks', type=int, default=2, show_default=True,
              help='nb. of processing tasks')
@click.option('--cleanup/--no-cleanup', default=False,
              help='do not cleanup saving directory')
@click.pass_context
def acquire(ctx, **kwargs):
    """Executes an acquisition"""
    interface = ctx.obj["interface"]

    class Options:
        def __init__(self, opts):
            self.__dict__.update(opts)

    options = Options(kwargs)

    with ReportTask('Initializing'):
        ctrl = Lima.Core.CtControl(interface)
    with ReportTask('Configuring'):
        configure(ctrl, options)
    try:
        with AcquisitionContext(ctrl) as acq_ctx:
            with ReportTask('Preparing'):
                acq_ctx.prepareAcq()
            with ReportTask('Acquiring', end='\n'):
                acq_ctx.startAcq()
                with AcqProgBar(ctrl, options) as prog_bar:
                    monitor = AcquisitionMonitor(acq_ctx, prog_bar, options)
                    monitor.run()
    except KeyboardInterrupt:
        pass
    finally:
        with ReportTask('Cleaning up') as task:
            if options.cleanup and options.saving_directory:
                cleanup(ctrl, options)
            else:
                task.skip()
