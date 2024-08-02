# Cf: https://opentelemetry.io/docs/languages/python/getting-started/#metrics
# sgu: the following command is the same as setting the following environment variables:
# export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
# opentelemetry-instrument \
#     --traces_exporter console \
#     --metrics_exporter console \
#     --logs_exporter console \
#     --service_name dice-server \
#     flask run -p 8080
# CAUTION: sgu setting the following environment variables in this file will not work, should do `source .env` instead
# os.environ['OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED']='true'
# os.environ['OTEL_LOGS_EXPORTER']='console'
# os.environ['OTEL_METRICS_EXPORTER']= 'console'
# os.environ['OTEL_TRACES_EXPORTER']='console'
# os.environ['OTEL_SERVICE_NAME']='dice-server'
# os.environ['PYTHONPATH']='/Users/shgu/Library/Caches/pypoetry/virtualenvs/tutorial-opentelemetry-xJY5D9Cr-py3.12/lib/python3.12/site-packages/opentelemetry/instrumentation/auto_instrumentation:/Users/shgu/repos-2/tutorial-opentelemetry'

from opentelemetry import trace
from opentelemetry import metrics

from random import randint
from flask import Flask, request
import logging

# Acquire a tracer
# "diceroller.tracer" is the uniquely identifiable name for instrumentation scope, such as instrumentation library, package, module or class name. __name__ may not be used as this can result in different tracer names if the tracers are in different files. It is better to use a fixed string that can be imported where needed and used consistently as the name of the tracer.  This should not be the name of the module that is instrumented but the name of the module doing the instrumentation. E.g., instead of "requests", use "opentelemetry.instrumentation.requests". Cf: https://opentelemetry-python.readthedocs.io/en/latest/api/trace.html#opentelemetry.trace.TracerProvider


tracer = trace.get_tracer("diceroller.tracer")

# Acquire a meter.
meter = metrics.get_meter("diceroller.meter")

# Now create a counter instrument to make measurements with
roll_counter = meter.create_counter(
	"dice.rolls",
	description="The number of rolls by roll value",
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/rolldice")
def roll_dice():
	# This creates a new span that's the child of the current one
	with tracer.start_as_current_span("roll") as roll_span:
		player = request.args.get('player', default = None, type = str)
		result = str(roll())
		roll_span.set_attribute("roll.value", result)
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