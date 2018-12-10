#!/usr/bin/env python
# -*- coding: utf-8 -*-
import rospy
from std_msgs.msg import String
import json
import sys
import MeCab
import voice_control_mode
import weather_forecast
(
    Left,
    Right,
) = range(0, 2)

def callback(msg):
    print(msg.data)
    words = parse(msg.data)
    print(words)
    if words == ['音声', '案内', 'モード', '開始']:
        voice_control_mode.Print_entering_message()
        return
    elif words == ['天気', '予報', 'モード', '開始']:
        weather_forecast.weather_forcast()
        return
    for word in words:
        if word == "止まれ":
            print("stop")
            publish_command(0)
            return
        elif word == "前" :
            print("go forward")
            publish_command(1)
            return
        elif word == "後ろ":
            print("go backward")
            publish_command(2)
            return
        elif word == "右":
            print("go right")
            publish_command(3)
            return
        elif word == "左":
            print("go left")
            publish_command(4)
            return
        #else:
        #    command = 0
        #    print("unknown command detected")
        #    return

def parse(text):
    m = MeCab.Tagger("-Ochasen")
    # m.prase('')
    node = m.parseToNode(text) 
    word_list = []
    while node:
        word = node.surface
        wclass = node.feature.split(',')
        if wclass[0] != 'BOS/EOS':
            word_list.append(word)
        node = node.next
    return word_list

motor_right = rospy.Publisher('/motor/right', String, queue_size=1)
motor_left = rospy.Publisher('/motor/left', String, queue_size=1)

def main():
    rospy.init_node('controller')
    
    # motor_right = rospy.Publisher('/motor/right', String, queue_size=1)
    # motor_left = rospy.Publisher('/motor/left', String, queue_size=1)

    #rospy.init_node('controller')
    #rospy.Subscriber('/speech', String, callback)
    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        rospy.Subscriber('/speech', String, callback)
        # publish_command(command)
        rate.sleep()

def publish_command(_command):
    if _command == 0:
        print("command = 0") # 止まれ
        motor_right.publish(generate_stop_command(Right, "soft"))
        motor_left.publish(generate_stop_command(Left, "soft"))
	return
    elif _command == 1:
        print("command = 1") # 前
        motor_right.publish(generate_run_command(Right, 1.0))
        motor_left.publish(generate_run_command(Left, 1.0))
	return
    elif _command == 2:
	print("command = 2") # 後ろ
	motor_right.publish(generate_run_command(Right, -1.0))
	motor_right.publish(generate_run_command(Left, -1.0))
	return
    elif _command == 3:
	print("command = 3") # 右
	motor_right.publish(generate_run_command(Right, -1.0))
	motor_left.publish(generate_run_command(Left, 1.0))
	return
    elif _command == 4:
	print("command = 4") # 左
	motor_right.publish(generate_run_command(Right, 1.0))
	motor_left.publish(generate_run_command(Left, -1.0))
	return
    #else:
    #    motor_right.publish(generate_message(Left, 1.0))
    #    motor_left.publish(generate_message(Right, 1.0))

def generate_run_command(motor, speed):
    scaling_constant = 100.0
    clamped_speed = max(-1.0, min(1.0, speed))
    regularized_speed = abs(clamped_speed * scaling_constant)
    direction = 'clockwise' if (motor == Right) == (speed >= 0.0) else 'counter-clockwise'
    message = {
        'command': 'run',
        'parameters': {
            'direction': direction,
            'speed': regularized_speed
            }
        }
    return json.dumps(message)

def generate_move_Command(motor):

    # TODO: 変更
    direction = 'clockwise' if (motor == Right) else 'counter-clockwise'
    # stepsどうする

    message = {
        'command': 'move',
        'parameters': {
            'direction': direction,
            'steps': ''
            }
        }
    return json.dumps(message)

def generate_goTo_command(motor, position):
    message = {
        'command': 'goTo',
        'parameters': {
            'position' : ''
            }
        }
    return json.dumps(message)

def generate_stop_command(motor, type):
    message = {
        'command': 'stop',
        'parameters': {
            'type' : type
            }
        }
    return json.dumps(message)

# def voice_control_mode():
#    print("enter voice control mode")
#    return

if __name__ == '__main__':
    main()
