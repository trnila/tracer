import logging
import os
import sys
from datetime import datetime

from tracer.extensions.extension import Extension
from tracer.report import Report


class ReportExtension(Extension):
    def create_options(self, parser):
        parser.add_argument('--no-report', '-n', help='Do not save any report', action='store_true', default=False)
        parser.add_argument('--output', '-o', help='Place monitored data directly in this directory')
        parser.add_argument('--directory', '-d', help='Create directory with monitored data in specified directory')
        parser.add_argument('--show-data', '-s', help='Print captured data to stdout', action="store_true",
                            default=False)

    def on_start(self, tracer):
        if not tracer.options.output:
            directory_name = 'tracer_{executable}_{date}'.format(
                executable=tracer.options.program.split('/')[-1],
                date=datetime.now().strftime("%d-%m-%Y_%H:%M:%S.%f")
            )

            target_dir = os.getcwd()
            if tracer.options.directory:
                target_dir = tracer.options.directory

            tracer.options.output = os.path.join(target_dir, directory_name)
        tracer.data = Report(None if tracer.options.no_report else tracer.options.output)

    def on_save(self, tracer):
        if tracer.options.no_report:
            return

        tracer.data.save()
        if tracer.options.show_data:
            tracer.data.save(sys.stdout)

        logging.info("Report saved in %s", tracer.options.output)
