#!/usr/bin/python


from MotorController import MotorController
from NetworkListener import NetworkListener
from RadioFlowGraph import RadioFlowGraph
from RadioListener import RadioListener
from multiprocessing import Process
from numpy import linspace
from pprint import pprint
import time


def main():

    net_listener = NetworkListener()
    net_listener.start()

    motor_controller = MotorController("/dev/ttyACM0", 115200)
    if motor_controller.connect():
        print("Successfully connected to motor controller.")
    else:
        print("Error: Motor controller not responding, verify connections.")
    motor_controller.reset_orientation()
    #pprint(motor_controller.get_current_angles())
    #pprint(motor_controller._get_controller_angles())
    #motor_controller.rotate_mast(5.0)
    #pprint(motor_controller.get_current_angles())
    #motor_controller.rotate_arm(25.0)
    #pprint(motor_controller.get_current_angles())
    #pprint(motor_controller._get_controller_angles())

    tx_radio_id = "hackrf=56a75f"
    rx_radio_id = "hackrf=61555f,buffers=4"
    #frequency = 914e6
    frequency = 2.42e9
    tx_freq_offset = 0
    #rx_freq_offset = -5e3
    rx_freq_offset = -7e3
    data_port = 8888

    radio_listener = RadioListener()
    radio_listener.start()

    radio_tx_graph = RadioFlowGraph(tx_radio_id, frequency, tx_freq_offset, data_port)
    radio_tx_graph.set_tx_gain(14, 47)
    radio_tx_graph.setup_flowgraph(transmitter=True)
    radio_rx_graph = RadioFlowGraph(rx_radio_id, frequency, rx_freq_offset, data_port)
    radio_rx_graph.setup_flowgraph(transmitter=False)

    # open antenna scan log file and add data header
    datafile_fp = open("antenna_data.txt", 'w')
    datafile_fp.write("% Mast Angle, Arm Angle, Background RSSI, Transmission RSSI\n")

    mast_start_angle = -180.0
    mast_end_angle = 180.0
    mast_steps = 181 # >= 1
    arm_start_angle = 0.0
    arm_end_angle = 0.0
    arm_steps = 1 # >= 1

    mast_angles = linspace(mast_start_angle, mast_end_angle, mast_steps)
    arm_angles = linspace(arm_start_angle, arm_end_angle, arm_steps)

    for mast_angle in mast_angles: # simulate n readings around antenna
        for arm_angle in arm_angles: # simulate n readings around antenna

            background_rssi = 0.0
            transmission_rssi = 0.0

            print("Target Mast Angle: "+str(mast_angle))
            print("Target Arm Angle: "+str(arm_angle))
            print("Moving antenna...")
            motor_controller.rotate_mast(mast_angle)
            motor_controller.rotate_arm(arm_angle)
            print("Movement complete")

            # background rssi reading
            print("Taking background noise sample...")
            radio_rx_graph.start()
            radio_rx_graph.wait()
            if radio_listener.is_data_available():
                background_rssi = radio_listener.get_data_average()
                print("Background RSSI: "+str(background_rssi))
            else:
                print("ERROR: Background RSSI unavailable!")
            #print("Sampling complete")

            # transmission rssi reading
            print("Taking transmitted signal sample...")
            radio_tx_graph.start()
            time.sleep(1.3) # give the transmitter flowgraph enough time to actually broadcast
            radio_rx_graph.start()
            radio_rx_graph.wait()
            radio_tx_graph.stop()
            radio_tx_graph.wait()
            if radio_listener.is_data_available():
                transmission_rssi = radio_listener.get_data_average()
                print("Transmission RSSI: "+str(transmission_rssi))
            else:
                print("ERROR: Transmission RSSI unavailable!")
            #print("Sampling complete")

            # write rssi readings to file
            print("Saving samples")
            datafile_fp.write(
                str(mast_angle) + ',' + 
                str(arm_angle) + ',' + 
                str(background_rssi) + ',' + 
                str(transmission_rssi) + '\n'
                )

    # return mast and arm to home position (0 degrees, 0 degrees)
    print("Returning mast and arm to home position...")
    motor_controller.rotate_mast(0)
    motor_controller.rotate_arm(0)
    print("Mast and arm should now be in home position")

    radio_listener.stop()

    net_listener.stop()




if __name__ == "__main__":
    main()

