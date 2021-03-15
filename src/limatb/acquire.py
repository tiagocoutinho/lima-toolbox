import os
import glob
import time
import signal
import pathlib

import click
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.shortcuts import ProgressBar

import Lima.Core
from Lima.Core import AcqRunning, AcqFault, FrameDim

from .util import (
    ur, ErrorMap, FileFormat, TriggerMode,
    SavingPolicy, SavingMode, SavingManagedMode,
)


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
    if options.saving_directory:
        fmt = FileFormat[options.saving_format.lower()]
        suffix = options.saving_suffix
        mode = SavingMode[options.saving_mode.lower()]
        managed_mode = SavingManagedMode[options.saving_managed_mode.lower()]
        policy = SavingPolicy[options.saving_policy.lower()]
        saving.setFormat(fmt)
        if suffix == AUTO_SUFFIX:
            saving.setFormatSuffix()
        else:
            saving.setSuffix(suffix)
        saving.setPrefix(options.saving_prefix)
        saving.setOverwritePolicy(policy)
        saving.setMaxConcurrentWritingTask(options.nb_saving_tasks)
        saving.setSavingMode(mode)
        saving.setManagedMode(managed_mode)
        saving.setDirectory(options.saving_directory)
        saving.setFramesPerFile(options.saving_nb_frames_per_file)
    acq.setAcqExpoTime(options.exposure_time)
    acq.setLatencyTime(options.latency_time)
    acq.setAcqNbFrames(options.nb_frames)
    acq.setTriggerMode(TriggerMode[options.trigger.lower()])
    buff.setMaxMemory(options.max_buffer_size)


def cleanup(ctrl, options):
    pattern = options.saving_prefix + '*' + options.saving_suffix
    pattern = pathlib.Path(options.saving_directory) / pattern
    for filename in glob.glob(str(pattern)):
        os.remove(filename)


def AcquisitionProgressBar(ctrl, options, **kwargs):
    iface = ctrl.hwInterface()
    info = iface.getHwCtrlObj(Lima.Core.HwCap.DetInfo)
    frame_dim = FrameDim(info.getDetectorImageSize(), info.getCurrImageType())
    exposure_time = options.exposure_time * ur.second
    latency_time = options.latency_time * ur.second
    frame_time = exposure_time + latency_time
    acq_time = (options.nb_frames * frame_time).to_compact()
    frame_rate = (1/frame_time).to(ur.Hz).to_compact()
    model = info.getDetectorModel()
    dtype = info.getDetectorType()
    if latency_time > 0:
        frame_time_str = f'({exposure_time:~.4} + {latency_time:~.4})'
    else:
        frame_time_str = f'{exposure_time:~.4}'
    title = f'Acquiring on {model} ({dtype}) | ' \
            f'{options.nb_frames} x {frame_time_str}({frame_rate:~.4}) = {acq_time:~.4}  | ' \
            f'{frame_dim}'
    kwargs["title"] = title
    return ProgressBar(**kwargs)


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


AUTO_SUFFIX = '__AUTO_SUFFIX__'


@click.command("acquire")
@click.option('-n', '--nb-frames', default=10, type=int, show_default=True)
@click.option('-e', '--exposure-time', default=0.1, type=float, show_default=True)
@click.option('-l', '--latency-time', default=0.0, type=float, show_default=True)
@click.option(
    '-t', '--trigger', default='int', show_default=True,
    type=click.Choice(TriggerMode, case_sensitive=False),
    help='trigger type'
)
@click.option('-d', '--saving-directory', default=None, type=str, show_default=True)
@click.option(
    '-f', '--saving-format', default='EDF',
    type=click.Choice(FileFormat, case_sensitive=False),
    help='saving format', show_default=True
)
@click.option(
    '-p', '--saving-policy', default='abort',
    type=click.Choice(SavingPolicy, case_sensitive=False),
    help='saving policy', show_default=True
)
@click.option(
    '--saving-managed-mode', default="software",
    type=click.Choice(SavingManagedMode, case_sensitive=False),
    help='saving managed mode', show_default=True
)
@click.option(
    '--saving-nb-frames-per-file', default=1,
    help="nb of frames per file"
)
@click.option(
    '--saving-mode', default="auto-frame",
    type=click.Choice(SavingMode, case_sensitive=False),
    help="saving mode"
)
@click.option('-p', '--saving-prefix', default='image_', type=str, show_default=True)
@click.option('-s', '--saving-suffix', default=AUTO_SUFFIX, type=str, show_default=True)
@click.option(
    '--frame-type', type=frame_type, default='Bpp16', show_default=True,
    help='pixel format (ex: Bpp8)')
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
    if interface is None:
        raise click.UsageError("missing detector", ctx)
    class Options:
        def __init__(self, opts):
            self.__dict__.update(opts)

    options = Options(kwargs)

    kb = KeyBindings()

    @kb.add('x')
    def _(event):
        " Send Abort (control-c) signal. "
        os.kill(os.getpid(), signal.SIGINT)

    tb_message = " <b>[x]</b> abort"

    if options.trigger == "int-mult":
        tb_message += " | <b>[t]</b> trigger"

        @kb.add('t')
        def _(event):
            acq_ctx.startAcq()

    if options.saving_directory and options.saving_mode.lower() == "manual":
        tb_message += " | <b>[s]</b> save last frame"

        @kb.add('s')
        def _(event):
            ctrl.saving().writeFrame()

    with ReportTask('Initializing'):
        ctrl = Lima.Core.CtControl(interface)
    with ReportTask('Configuring'):
        configure(ctrl, options)
    try:
        with AcquisitionContext(ctrl) as acq_ctx:
            with ReportTask('Preparing'):
                acq_ctx.prepareAcq()
            with ReportTask('Acquiring', end='\n'):
                prog_bar = AcquisitionProgressBar(ctrl, options,
                    bottom_toolbar=HTML(tb_message),
                    key_bindings=kb,
                )
                with prog_bar:
                    acq_ctx.startAcq()
                    monitor = AcquisitionMonitor(acq_ctx, prog_bar, options)
                    monitor.run()
    except KeyboardInterrupt:
        print("Ctrl-C pressed")
    finally:
        with ReportTask('Cleaning up') as task:
            if options.cleanup and options.saving_directory:
                cleanup(ctrl, options)
            else:
                task.skip()
