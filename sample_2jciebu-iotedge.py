import serial
import random
import time
import sys
import iothub_client
from iothub_client import IoTHubClient, IoTHubClientError,IoTHubModuleClient, IoTHubTransportProvider, IoTHubClientResult
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError, DeviceMethodReturnValue
from iothub_client import IoTHubClientRetryPolicy, GetRetryPolicyReturnValue
from iothub_client_args import get_iothub_opt, OptionError




from datetime import datetime

# LED display rule. Normal Off.
DISPLAY_RULE_NORMALLY_OFF = 0

# LED display rule. Normal On.
DISPLAY_RULE_NORMALLY_ON = 1

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubClient.send_event_async.
# By default, messages do not expire.
MESSAGE_TIMEOUT = 10000

RECEIVE_CONTEXT = 0
AVG_WIND_SPEED = 10.0
MIN_TEMPERATURE = 20.0
MIN_HUMIDITY = 60.0
MESSAGE_COUNT = 0
RECEIVED_COUNT = 0
CONNECTION_STATUS_CONTEXT = 0
TWIN_CONTEXT = 0
SEND_REPORTED_STATE_CONTEXT = 0
METHOD_CONTEXT = 0

# global counters
RECEIVE_CALLBACKS = 0
SEND_CALLBACKS = 0
BLOB_CALLBACKS = 0
CONNECTION_STATUS_CALLBACKS = 0
TWIN_CALLBACKS = 0
SEND_REPORTED_STATE_CALLBACKS = 0
METHOD_CALLBACKS = 0

# chose HTTP, AMQP, AMQP_WS or MQTT as transport protocol
PROTOCOL = IoTHubTransportProvider.AMQP

# String containing Hostname, Device Id & Device Key in the format:
# "HostName=<host_name>;DeviceId=<device_id>;SharedAccessKey=<device_key>"
CONNECTION_STRING = "[Device Connection String]"
TEXT_MESSAGE_TO_IOTHUB = ""

def set_certificates(client):
    from iothub_client_cert import CERTIFICATES
    try:
        client.set_option("TrustedCerts", CERTIFICATES)
        print ( "set_option TrustedCerts successful" )
    except IoTHubClientError as iothub_client_error:
        print ( "set_option TrustedCerts failed (%s)" % iothub_client_error )

def receive_message_callback(message, counter):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "Received Message [%d]:" % counter )
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    counter += 1
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    return IoTHubMessageDispositionResult.ACCEPTED


def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    print ( "Confirmation[%d] received for message with result = %s" % (user_context, result) )
    map_properties = message.properties()
    print ( "    message_id: %s" % message.message_id )
    print ( "    correlation_id: %s" % message.correlation_id )
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    SEND_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_CALLBACKS )


def connection_status_callback(result, reason, user_context):
    global CONNECTION_STATUS_CALLBACKS
    print ( "Connection status changed[%d] with:" % (user_context) )
    print ( "    reason: %d" % reason )
    print ( "    result: %s" % result )
    CONNECTION_STATUS_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % CONNECTION_STATUS_CALLBACKS )

# receive_message_callback is invoked when an incoming message arrives on the specified 
# input queue (in the case of this sample, "input1").  Because this is a filter module, 
# we will forward this message onto the "output1" queue.
def receive_message_callback(message, hubManager):
    global RECEIVE_CALLBACKS
    message_buffer = message.get_bytearray()
    size = len(message_buffer)
    print ( "    Data: <<<%s>>> & Size=%d" % (message_buffer[:size].decode('utf-8'), size) )
    map_properties = message.properties()
    key_value_pair = map_properties.get_internals()
    print ( "    Properties: %s" % key_value_pair )
    RECEIVE_CALLBACKS += 1
    print ( "    Total calls received: %d" % RECEIVE_CALLBACKS )
    hubManager.forward_event_to_output("outputcommandresponse", message, 0)
    return IoTHubMessageDispositionResult.ACCEPTED


# module_twin_callback is invoked when the module twin's desired properties are updated.
def module_twin_callback(update_state, payload, user_context):
    global TWIN_CALLBACKS
    global TEMPERATURE_THRESHOLD
    print ( "\nTwin callback called with:\nupdateStatus = %s\npayload = %s\ncontext = %s" % (update_state, payload, user_context) )
    data = json.loads(payload)
    if "desired" in data and "TemperatureThreshold" in data["desired"]:
        TEMPERATURE_THRESHOLD = data["desired"]["TemperatureThreshold"]
    if "TemperatureThreshold" in data:
        TEMPERATURE_THRESHOLD = data["TemperatureThreshold"]
    TWIN_CALLBACKS += 1
    print ( "Total calls confirmed: %d\n" % TWIN_CALLBACKS )



def send_reported_state_callback(status_code, user_context):
    global SEND_REPORTED_STATE_CALLBACKS
    print ( "Confirmation[%d] for reported state received with:" % (user_context) )
    print ( "    status_code: %d" % status_code )
    SEND_REPORTED_STATE_CALLBACKS += 1
    print ( "    Total calls confirmed: %d" % SEND_REPORTED_STATE_CALLBACKS )


def module_method_callback(method_name, payload, user_context):
    global METHOD_CALLBACKS
    print ( "\nMethod callback called with:\nmethodName = %s\npayload = %s\ncontext = %s" % (method_name, payload, user_context) )
    METHOD_CALLBACKS += 1
    print ( "Total calls confirmed: %d\n" % METHOD_CALLBACKS )
    device_method_return_value = DeviceMethodReturnValue()
    device_method_return_value.response = "{ \"Response\": \"This is the response from the device\" }"
    device_method_return_value.status = 200
    return device_method_return_value


# for IoT Edge Runtime 
class HubManager(object):
    def __init__(
            self,
            protocol):
        print ("Initializing IoT Ede Module Client...")
        self.client_protocol = protocol
        self.client = IoTHubModuleClient()
        self.client.create_from_environment(protocol)
        # set the time until a message times out
        self.client.set_option("messageTimeout", MESSAGE_TIMEOUT)
        # set to increase logging level
        # self.client.set_option("logtrace", 1)
        self.client.set_message_callback("inputcommand", receive_message_callback, self)

        # Sets the callback when a module twin's desired properties are updated.
        self.client.set_module_twin_callback(module_twin_callback, self)
        self.client.set_module_method_callback(module_method_callback,self)
        


    # Sends a message to the queue with outputQueueName, "temperatureOutput" in the case of the sample.
    def send_event_to_output(self, outputQueueName, event, properties, send_context):
        if not isinstance(event, IoTHubMessage):
            event = IoTHubMessage(bytearray(event, 'utf8'))

        if len(properties) > 0:
            prop_map = event.properties()
            for key in properties:
                prop_map.add_or_update(key, properties[key])

        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)

    def send_reported_state(self, reported_state, size, reported_context ):
        self.client.send_reported_state(reported_state, size,send_reported_state_callback , reported_context)

    def forward_event_to_output(self, outputQueueName, event, send_context):
        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)


def calc_crc(buf, length):
    """
    CRC-16 calculation.

    """
    crc = 0xFFFF
    for i in range(length):
        crc = crc ^ buf[i]
        for i in range(8):
            carrayFlag = crc & 1
            crc = crc >> 1
            if (carrayFlag == 1):
                crc = crc ^ 0xA001
    crcH = crc >> 8
    crcL = crc & 0x00FF
    return (bytearray([crcL, crcH]))


def print_latest_data(data):
    """
    print measured latest value.
    """
    time_measured = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    temperature = str(int(hex(data[9]) + format(data[8], 'x'), 16) / 100)
    relative_humidity = str(int(hex(data[11]) + format(data[10], 'x'), 16) / 100)
    ambient_light = str(int(hex(data[13]) + format(data[12], 'x'), 16))
    barometric_pressure = str(
        int(hex(data[17]) + format(data[16], 'x') + format(data[15], 'x') + format(data[14], 'x'), 16) / 1000)
    sound_noise = str(int(hex(data[19]) + format(data[18], 'x'), 16) / 100)
    eTVOC = str(int(hex(data[21]) + format(data[20], 'x'), 16))
    eCO2 = str(int(hex(data[23]) + format(data[22], 'x'), 16))
    discomfort_index = str(int(hex(data[25]) + format(data[24], 'x'), 16) / 100)
    heat_stroke = str(int(hex(data[27]) + format(data[26], 'x'), 16) / 100)
    vibration_information = str(int(hex(data[28]), 16))
    si_value = str(int(hex(data[30]) + format(data[29], 'x'), 16) / 10)
    pga = str(int(hex(data[32]) + format(data[31], 'x'), 16) / 10)
    seismic_intensity = str(int(hex(data[34]) + format(data[33], 'x'), 16) / 1000)
    temperature_flag = str(int(hex(data[36]) + format(data[35], 'x'), 16))
    relative_humidity_flag = str(int(hex(data[38]) + format(data[37], 'x'), 16))
    ambient_light_flag = str(int(hex(data[40]) + format(data[39], 'x'), 16))
    barometric_pressure_flag = str(int(hex(data[42]) + format(data[41], 'x'), 16))
    sound_noise_flag = str(int(hex(data[44]) + format(data[43], 'x'), 16))
    etvoc_flag = str(int(hex(data[46]) + format(data[45], 'x'), 16))
    eco2_flag = str(int(hex(data[48]) + format(data[47], 'x'), 16))
    discomfort_index_flag = str(int(hex(data[50]) + format(data[49], 'x'), 16))
    heat_stroke_flag = str(int(hex(data[52]) + format(data[51], 'x'), 16))
    si_value_flag = str(int(hex(data[53]), 16))
    pga_flag = str(int(hex(data[54]), 16))
    seismic_intensity_flag = str(int(hex(data[55]), 16))
    print("")
    print("Time measured:" + time_measured)
    print("Temperature:" + temperature)
    print("Relative humidity:" + relative_humidity)
    print("Ambient light:" + ambient_light)
    print("Barometric pressure:" + barometric_pressure)
    print("Sound noise:" + sound_noise)
    print("eTVOC:" + eTVOC)
    print("eCO2:" + eCO2)
    print("Discomfort index:" + discomfort_index)
    print("Heat stroke:" + heat_stroke)
    print("Vibration information:" + vibration_information)
    print("SI value:" + si_value)
    print("PGA:" + pga)
    print("Seismic intensity:" + seismic_intensity)
    print("Temperature flag:" + temperature_flag)
    print("Relative humidity flag:" + relative_humidity_flag)
    print("Ambient light flag:" + ambient_light_flag)
    print("Barometric pressure flag:" + barometric_pressure_flag)
    print("Sound noise flag:" + sound_noise_flag)
    print("eTVOC flag:" + etvoc_flag)
    print("eCO2 flag:" + eco2_flag)
    print("Discomfort index flag:" + discomfort_index_flag)
    print("Heat stroke flag:" + heat_stroke_flag)
    print("SI value flag:" + si_value_flag)
    print("PGA flag:" + pga_flag)
    print("Seismic intensity flag:" + seismic_intensity_flag)
    TEXT_MESSAGE_TO_IOTHUB = MSG_TXT % (time_measured, barometric_pressure, temperature, relative_humidity)
    print("Send to be ...:" + TEXT_MESSAGE_TO_IOTHUB)
    return TEXT_MESSAGE_TO_IOTHUB

def now_utc_str():
    """
    Get now utc.
    """
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

MSG_TXT = "{\"measured_time\": \"%s\", \"Barometric\": %s,\"temperature\": %s,\"humidity\": %s}"

if __name__ == '__main__':

    # Serial.
    ser = serial.Serial("/dev/ttyUSB0", 115200, serial.EIGHTBITS, serial.PARITY_NONE)

    try:
        # IoT Hub Connection
     #   client = iothub_client_init()

        hub_manager = HubManager(IoTHubTransportProvider.MQTT)

        reported_state = "{\"newState\":\"standBy\"}"
        hub_manager.send_reported_state(reported_state, len(reported_state), SEND_REPORTED_STATE_CONTEXT)

        # LED On. Color of Green.
        command = bytearray([0x52, 0x42, 0x0a, 0x00, 0x02, 0x11, 0x51, DISPLAY_RULE_NORMALLY_ON, 0x00, 0, 255, 0])
        command = command + calc_crc(command, len(command))
        ser.write(command)
        time.sleep(0.1)
        ret = ser.read(ser.inWaiting())

        while ser.isOpen():
            # Get Latest data Long.
            command = bytearray([0x52, 0x42, 0x05, 0x00, 0x01, 0x21, 0x50])
            command = command + calc_crc(command, len(command))
            tmp = ser.write(command)
            time.sleep(0.1)
            data = ser.read(ser.inWaiting())
            message = print_latest_data(data)
            iot_message = IoTHubMessage(message)
            print("Create IoT Hub Message with : "+message)
            msg_properties = {}
            hub_manager.send_event_to_output("sensoroutput", iot_message, msg_properties, MESSAGE_COUNT)
            MESSAGE_COUNT = MESSAGE_COUNT + 1
            
            time.sleep(1)

    except KeyboardInterrupt:
        # LED Off.
        command = bytearray([0x52, 0x42, 0x0a, 0x00, 0x02, 0x11, 0x51, DISPLAY_RULE_NORMALLY_OFF, 0x00, 0, 0, 0])
        command = command + calc_crc(command, len(command))
        ser.write(command)
        time.sleep(1)
        # script finish.
        sys.exit
