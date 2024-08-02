# to run, simply do: python app-manual.py
import logging
from random import randint
from flask import Flask, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


### sgu adapted from https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/monitor/azure-monitor-opentelemetry-exporter#export-exceptions-log
# pylint: disable=wrong-import-position
from opentelemetry import trace
from opentelemetry import metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk._logs.export import ConsoleLogExporter
#from opentelemetry.semconv.trace import SpanAttributes Cf: https://opentelemetry.io/docs/languages/python/instrumentation/#add-semantic-attributes

from opentelemetry._logs import (
    get_logger_provider,
    set_logger_provider,
)
from opentelemetry.sdk._logs import (
    LoggerProvider,
    LoggingHandler,
)

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.metrics import get_meter_provider, set_meter_provider

# sgu: Set up the TracerProvider which is global then.
trace.set_tracer_provider(TracerProvider())

# # sgu: SpanProcessor decides when to flush and export to where. SimpleSpanProcessor simply export synchronously when the span context ends Cf: https://vscode.dev/github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/export/__init__.py#L93
console_span_exporter = ConsoleSpanExporter()
span_processor = SimpleSpanProcessor(console_span_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)


## setup log exporter 
set_logger_provider(LoggerProvider())
exporter = ConsoleLogExporter()
get_logger_provider().add_log_record_processor(BatchLogRecordProcessor(exporter))

# Attach LoggingHandler to namespaced logger
handler = LoggingHandler() # sgu: this handler points to the global LogProvider setup above.  
logger = logging.getLogger(__name__)
logger.addHandler(handler)
#logger.setLevel(logging.NOTSET)
logger.setLevel(logging.INFO)

# Set up the MeterProvider: sgu: this seems to need some packages which can be installed via `opentelemetry-bootstrap -a install`
console_metric_exporter = ConsoleMetricExporter()
# sgu: this will emit a meter record every 5 seconds. The __init__ method starts a thread to _tick  which checks if the metric is not None and call the exported if needed. Cf: https://vscode.dev/github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/metrics/_internal/export/__init__.py#L428
metric_reader = PeriodicExportingMetricReader(console_metric_exporter, export_interval_millis=5000)
# Set the global meter provider
set_meter_provider(MeterProvider(metric_readers=[metric_reader]))

## end sgu adapted from


# Acquire a tracer
# "diceroller.tracer" is the uniquely identifiable name for instrumentation scope, such as instrumentation library, package, module or class name. __name__ may not be used as this can result in different tracer names if the tracers are in different files. It is better to use a fixed string that can be imported where needed and used consistently as the name of the tracer.  This should not be the name of the module that is instrumented but the name of the module doing the instrumentation. E.g., instead of "requests", use "opentelemetry.instrumentation.requests". Cf: https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html#opentelemetry.trace.TracerProvider
 # sgu: it looks like not all trace_provider export the instrumentation scope
  # sgu: the get_tracer method might return a new Tracer  for each call, but all Tracers points to TraceProvider._active_span_processor Cf: https://vscode.dev/github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py#L1260-L1261
  # the tracer also handles the sampling logic in Tracer.start_span Cf: https://vscode.dev/github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py#L1110

#tracer = trace.get_tracer("diceroller.tracer")
tracer = trace.get_tracer("sgu-tracer")

# Acquire a meter.
meter = metrics.get_meter("diceroller.meter")

# Now create a counter instrument to make measurements with
roll_counter = meter.create_counter(
	"dice.rolls",
	description="The number of rolls by roll value",
)


@app.route("/rolldice")
def roll_dice():
	# This creates a new span that's the child of the current one
	with tracer.start_as_current_span("roll") as roll_span:
		player = request.args.get('player', default = None, type = str)
		result = str(roll())
		roll_span.set_attribute("roll.value", result)
		roll_span.set_attribute("x-ms-user", request.headers.get("x-ms-user", "unknown"))
		# This adds 1 to the counter for the given roll value
		roll_counter.add(1, {"roll.value": result})
		if player:
			logger.warning("%s is rolling the dice: %s", player, result)
		else:
			logger.warning("Anonymous player is rolling the dice: %s", result)
		return result

def roll():
	return randint(1, 6)

if __name__ == "__main__":
     app.run(port=8080)