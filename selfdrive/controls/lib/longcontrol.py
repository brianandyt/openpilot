from cereal import log
from common.numpy_fast import clip, interp
from selfdrive.controls.lib.pid import PIController

LongCtrlState = log.ControlsState.LongControlState

STOPPING_EGO_SPEED = 0.5
MIN_CAN_SPEED = 0.3  # TODO: parametrize this in car interface
STOPPING_TARGET_SPEED = MIN_CAN_SPEED + 0.01
STARTING_TARGET_SPEED = 0.5
BRAKE_THRESHOLD_TO_PID = 0.2

STOPPING_BRAKE_RATE = 0.2  # brake_travel/s while trying to stop
STARTING_BRAKE_RATE = 0.8  # brake_travel/s while releasing on restart
BRAKE_STOPPING_TARGET = 0.7  # apply at least this amount of brake to maintain the vehicle stationary

RATE = 100.0


def long_control_state_trans(active, long_control_state, v_ego, v_target, v_pid,
                             output_gb, brake_pressed, cruise_standstill):
  """Update longitudinal control state machine"""
  stopping_condition = (v_ego < 2.0 and cruise_standstill) or \
                       (v_ego < STOPPING_EGO_SPEED and
                        ((v_pid < STOPPING_TARGET_SPEED and v_target < STOPPING_TARGET_SPEED) or
                        brake_pressed))

  starting_condition = v_target > STARTING_TARGET_SPEED and not cruise_standstill

  if not active:
    long_control_state = LongCtrlState.off

  else:
    if long_control_state == LongCtrlState.off:
      if active:
        long_control_state = LongCtrlState.pid

    elif long_control_state == LongCtrlState.pid:
      if stopping_condition:
        long_control_state = LongCtrlState.stopping

    elif long_control_state == LongCtrlState.stopping:
      if starting_condition:
        long_control_state = LongCtrlState.starting

    elif long_control_state == LongCtrlState.starting:
      if stopping_condition:
        long_control_state = LongCtrlState.stopping
      elif output_gb >= -BRAKE_THRESHOLD_TO_PID:
        long_control_state = LongCtrlState.pid

  return long_control_state


class LongControl():
  def __init__(self, CP, compute_gb):
    self.long_control_state = LongCtrlState.off  # initialized to off
    self.pid = PIController((CP.longitudinalTuning.kpBP, CP.longitudinalTuning.kpV),
                            (CP.longitudinalTuning.kiBP, CP.longitudinalTuning.kiV),
                            rate=RATE,
                            sat_limit=0.8,
                            convert=compute_gb)
    self.v_pid = 0.0
    self.last_output_gb = 0.0

  def reset(self, v_pid):
    """Reset PID controller and change setpoint"""
    self.pid.reset()
    self.v_pid = v_pid

  def dynamic_gas(self, v_ego, gas_interceptor):
    dynamic = False
    if gas_interceptor:
        dynamic = True
        x = [0.0, 1.4082, 2.80311, 4.22661, 5.38271, 6.16561, 7.24781, 8.28308, 10.24465, 12.96402, 15.42303, 18.11903, 20.11703, 24.46614, 29.05805, 32.71015, 35.76326]
        y = [0.3, 0.304, 0.315, 0.342, 0.365, 0.386, 0.429, 0.454, 0.472, 0.48, 0.489, 0.421, 0.432, 0.480, 0.55, 0.56, 0.59]
    else:
        dynamic = True
        x = [0.0, 1.4082, 2.80311, 4.22661, 5.38271, 6.16561, 7.24781, 8.28308, 10.24465, 12.96402, 15.42303, 18.11903, 20.11703, 24.46614, 29.05805, 32.71015, 35.76326]
        y = [0.2, 0.20443, 0.21592, 0.23334, 0.25734, 0.27916, 0.3229, 0.34784, 0.36765, 0.38, 0.396, 0.409, 0.425, 0.478, 0.48, 0.51, 0.55]
    if not dynamic:
      x = [0., 9., 55.]  # default BP values

    accel = interp(v_ego, x, y)

    #if dynamic and hasLead:  # dynamic gas profile specific operations, and if lead
    #  if v_ego < 6.7056:  # if under 15 mph
    #    x = [1.61479, 1.99067, 2.28537, 2.49888, 2.6312, 2.68224]
    #    y = [-accel, -(accel / 1.06), -(accel / 1.2), -(accel / 1.8), -(accel / 4.4), 0]  # array that matches current chosen accel value
    #    accel += interp(vRel, x, y)
    #  else:
    #    x = [-0.89408, 0, 0.89408, 4.4704]
    #    y = [-.15, -.05, .005, .05]
    #    accel += interp(vRel, x, y)

    min_return = 0.0
    max_return = 1.0
    return round(max(min(accel, max_return), min_return), 5)  # ensure we return a value between range

  def update(self, active, CS, v_target, v_target_future, a_target, CP, hasLead):
    """Update longitudinal control. This updates the state machine and runs a PID loop"""
    try:
      gas_interceptor = CP.enableGasInterceptor
    except AttributeError:
      gas_interceptor = False
    # Actuation limits
    gas_max = self.dynamic_gas(CS.vEgo, gas_interceptor)
    brake_max = interp(CS.vEgo, CP.brakeMaxBP, CP.brakeMaxV)

    # Update state machine
    output_gb = self.last_output_gb
    self.long_control_state = long_control_state_trans(active, self.long_control_state, CS.vEgo,
                                                       v_target_future, self.v_pid, output_gb,
                                                       CS.brakePressed, CS.cruiseState.standstill)

    v_ego_pid = max(CS.vEgo, MIN_CAN_SPEED)  # Without this we get jumps, CAN bus reports 0 when speed < 0.3

    if self.long_control_state == LongCtrlState.off or CS.gasPressed or CS.brakePressed:
      self.reset(v_ego_pid)
      output_gb = 0.

    # tracking objects and driving
    elif self.long_control_state == LongCtrlState.pid:
      self.v_pid = v_target
      self.pid.pos_limit = gas_max
      self.pid.neg_limit = - brake_max

      # Toyota starts braking more when it thinks you want to stop
      # Freeze the integrator so we don't accelerate to compensate, and don't allow positive acceleration
      prevent_overshoot = not CP.stoppingControl and CS.vEgo < 1.5 and v_target_future < 0.7
      deadzone = interp(v_ego_pid, CP.longitudinalTuning.deadzoneBP, CP.longitudinalTuning.deadzoneV)

      output_gb = self.pid.update(self.v_pid, v_ego_pid, speed=v_ego_pid, deadzone=deadzone, feedforward=a_target, freeze_integrator=prevent_overshoot)

      if prevent_overshoot:
        output_gb = min(output_gb, 0.0)

    # Intention is to stop, switch to a different brake control until we stop
    elif self.long_control_state == LongCtrlState.stopping:
      # Keep applying brakes until the car is stopped
      factor = 1
      if hasLead:
        factor = interp(dRel,[2.0,3.0,4.0,5.0,6.0,7.0,8.0], [3.0,2.1,1.5,1.0,0.6,0.29,0.0])
      if not CS.standstill or output_gb > -BRAKE_STOPPING_TARGET:
        output_gb -= STOPPING_BRAKE_RATE / RATE * factor
      output_gb = clip(output_gb, -brake_max, gas_max)

      self.reset(CS.vEgo)

    # Intention is to move again, release brake fast before handing control to PID
    elif self.long_control_state == LongCtrlState.starting:
      factor = 1
      if hasLead:
        factor = interp(dRel,[0.0,2.0,4.0,6.0], [0.0,0.5,1.0,2.0])
      if output_gb < -0.2:
        output_gb += STARTING_BRAKE_RATE / RATE * factor
      self.v_pid = CS.vEgo
      self.pid.reset()

    self.last_output_gb = output_gb
    final_gas = clip(output_gb, 0., gas_max)
    final_brake = -clip(output_gb, -brake_max, 0.)

    return final_gas, final_brake
