import sys

from tracer.extensions.extension import Extension
from tracer.report import Report


class ReportExtension(Extension):
    def create_options(self, parser):
        parser.add_argument('--output', '-o')
        parser.add_argument('--print-data', '-d', help='print captured data to stdout', action="store_true",
                            default=False)

    def on_start(self, tracer):
        print(tracer.options)
        tracer.data = Report(tracer.options.output)

    def on_save(self, tracer):
        tracer.data.save()
        if tracer.options.print_data:
            tracer.data.save(sys.stdout)

        print("Report saved in %s" % tracer.options.output)
