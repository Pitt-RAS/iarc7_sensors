#!/usr/bin/env python
import sys
import rospy
import tf2_geometry_msgs
import tf2_ros

from iarc7_msgs.msg import BoolStamped
from iarc7_msgs.msg import LandingGearContactsStamped
from geometry_msgs.msg import PointStamped, TwistWithCovarianceStamped
from nav_msgs.msg import Odometry

from iarc7_safety.SafetyClient import SafetyClient

def switch_callback(msg):
    global last_switch_message
    last_switch_message = msg

def odometry_callback(msg):
    global odometry
    odometry = msg

last_switch_message = None
height_indicates_landed = False
velocity_indicates_landed = False
rospy.init_node('landing_detector')
current_time = rospy.Time.now()
last_time = rospy.Time.now()

if __name__ == '__main__':
    absolute_velocity_pub = rospy.Publisher('absolute_vel', TwistWithCovarianceStamped, queue_size=0)
    landing_detected_pub = rospy.Publisher('landing_detected', BoolStamped, queue_size=0)

    rate = rospy.Rate(rospy.get_param('~update_rate'))

    tf_buffer = tf2_ros.Buffer()
    tf_listener = tf2_ros.TransformListener(tf_buffer)

    landing_detected_height = rospy.get_param('~landing_detected_height')
    takeoff_detected_height = rospy.get_param('~takeoff_detected_height')
    min_velocity_threshold = rospy.get_param('~min_velocity_threshold')
    min_velocity_duration = rospy.get_param('~min_velocity_duration')
    velocity_detector_height =  rospy.get_param('~velocity_detector_height')
    rospy.Subscriber('odometry/filtered', Odometry, odometry_callback)
    use_switches = rospy.get_param('~use_switches')

    if use_switches:
        takeoff_detected_override_height = rospy.get_param('~takeoff_detected_override_height')
        switch_expected_update_rate = rospy.get_param('~switch_expected_update_rate')
        switch_update_lag_tolerance = rospy.get_param('~switch_update_lag_tolerance')
        switch_startup_timeout = rospy.get_param('~switch_startup_timeout')
        rospy.Subscriber('landing_gear_contact_switches', LandingGearContactsStamped, switch_callback)

    # Wait for a valid timestamp
    while rospy.Time.now() == rospy.Time(0):
        if rospy.is_shutdown():
            raise rospy.exceptions.ROSInterruptException('No valid timestamp before shutdown')
        rate.sleep()

    # Make sure a message is recieved and published before connecting
    # to safety
    start_time = rospy.Time.now()

    if use_switches:
        while last_switch_message is None:
            assert((rospy.Time.now() - start_time) < rospy.Duration(switch_startup_timeout))
            if rospy.is_shutdown():
                raise rospy.exceptions.ROSInterruptException('No message before shutdown')
            rate.sleep()

    safety_client = SafetyClient('landing_detector')
    assert(safety_client.form_bond())

    # Wait for valid transform
    while not rospy.is_shutdown() and not tf_buffer.can_transform(
            'map',
            'base_footprint',
            rospy.Time(0)):
        # Publish the ground state message assuming we are on the ground
        state_msg = BoolStamped()
        state_msg.header.stamp = rospy.Time.now()
        state_msg.data = True
        landing_detected_pub.publish(state_msg)
        rate.sleep()

    while not rospy.is_shutdown():
        if (safety_client.is_fatal_active()
           or safety_client.is_safety_active()):
            # We don't have a safety response for this node so just exit
            break

        # Make sure we are within the target update rate
        if use_switches:
            if ((rospy.Time.now() - last_switch_message.header.stamp)
                > rospy.Duration(1.0/(switch_expected_update_rate
                                      -switch_update_lag_tolerance))):
                rospy.logwarn_throttle(1.0,
                    'Landing Detector is not receiving switch messages fast enough')

        # If this fails something is seriously wrong, so we're ok with crashing
        last_tf = tf_buffer.lookup_transform('map',
                                             'base_footprint',
                                             rospy.Time(0))
        point = PointStamped()
        point = tf2_geometry_msgs.do_transform_point(point, last_tf)
        last_height = point.point.z

        # detects if we are at really low height
        if height_indicates_landed:
            height_indicates_landed = last_height < takeoff_detected_height
        else:
            height_indicates_landed = last_height < landing_detected_height

        # detects if we are at really low speed
        if (abs(odometry.twist.twist.linear.z) < min_velocity_threshold) and (last_height < velocity_detector_height):
            current_time = rospy.Time.now()
        else:
            last_time = rospy.Time.now()
        velocity_indicates_landed = (current_time-last_time) > rospy.Duration(min_velocity_duration)

        # aggregates all signals
        if use_switches:
            landing_detected = ((last_switch_message.front
                                + last_switch_message.back
                                + last_switch_message.left
                                + last_switch_message.right
                                + height_indicates_landed
                                + velocity_indicates_landed) > 3
                                and last_height <= takeoff_detected_override_height)
        else:
            landing_detected = velocity_indicates_landed or height_indicates_landed


        if landing_detected:
            # Publish the fact that the velocity is 0
            vel_msg = TwistWithCovarianceStamped()
            vel_msg.header.frame_id = 'map'
            vel_msg.header.stamp = rospy.Time.now()
            absolute_velocity_pub.publish(vel_msg)

        # Publish the ground state message
        state_msg = BoolStamped()
        state_msg.header.stamp = rospy.Time.now()
        state_msg.data = landing_detected
        landing_detected_pub.publish(state_msg)

        rate.sleep()
