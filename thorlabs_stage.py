import sys
import time
import os
import clr # pythonnet

# 默认 Kinesis 安装路径
KINESIS_PATH = r"C:\Program Files\Thorlabs\Kinesis"

# 确保路径存在
if KINESIS_PATH not in sys.path:
    sys.path.append(KINESIS_PATH)

class ThorlabsStage:
    """
    Thorlabs KCube DC Servo 电机控制类
    支持 PRM1-Z8 (旋转) 和 Z825B (Z轴)
    """

    def __init__(self, stage_type=2):
        """
        初始化控制器参数，但不立即连接硬件。
        :param stage_type: 1 = PRM1-Z8 (Rotation), 2 = Z825B (Z-Axis)
        """
        self.stage_type = stage_type
        self.device = None
        self.is_connected = False
        
        # 根据类型设置序列号和配置名称
        if stage_type == 1:
            self.serial_no = '27266129'
            self.settings_name = 'PRM1-Z8'
        elif stage_type == 2:
            self.serial_no = '27257441'
            self.settings_name = 'Z825B'
        else:
            raise ValueError(f"Unsupported stage type: {stage_type}")

        # 加载必要的 DLL
        self._load_dlls()

    def _load_dlls(self):
        """加载 Thorlabs .NET DLLs (内部方法)"""
        try:
            clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
            clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
            clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
            
            # 导入命名空间
            from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
            from Thorlabs.MotionControl.DeviceManagerCLI import DeviceSettingsSectionBase
            from Thorlabs.MotionControl.KCube.DCServoCLI import KCubeDCServo
            from Thorlabs.MotionControl.GenericMotorCLI import KCubeMotor
            
            # 保存引用以便类中其他方法使用
            self.DeviceManagerCLI = DeviceManagerCLI
            self.DeviceSettingsSectionBase = DeviceSettingsSectionBase
            self.KCubeDCServo = KCubeDCServo
            self.KCubeMotor = KCubeMotor
            
        except Exception as e:
            raise RuntimeError(f"DLL Load Error: {e}. Check Kinesis installation.")

    def connect(self):
        """连接设备并应用设置"""
        print(f"Connecting to {self.settings_name} ({self.serial_no})...")
        
        # 建立设备列表
        self.DeviceManagerCLI.BuildDeviceList()
        
        try:
            # 创建并连接设备
            self.device = self.KCubeDCServo.CreateKCubeDCServo(self.serial_no)
            self.device.Connect(self.serial_no)
            
            # 等待设置初始化
            if not self.device.IsSettingsInitialized():
                self.device.WaitForSettingsInitialized(5000)
            
            self.device.StartPolling(250)
            self.device.EnableDevice()
            time.sleep(1) # 等待使能稳定

            # 加载电机配置 (LoadMotorConfiguration)
            print("Loading motor configuration...")
            motor_config = self.device.LoadMotorConfiguration(self.serial_no)
            
            # 设置加载选项为 UseFileSettings (对应 MATLAB optionTypeEnums.Get(1))
            motor_config.LoadSettingsOption = \
                self.DeviceSettingsSectionBase.SettingsUseOptionType.UseFileSettings
            motor_config.DeviceSettingsName = self.settings_name
            
            # 应用设置
            factory = self.KCubeMotor.KCubeDCMotorSettingsFactory()
            self.device.SetSettings(factory.GetSettings(motor_config), True, False)
            
            self.is_connected = True
            print("Device connected and settings loaded.")
            
        except Exception as e:
            self.is_connected = False
            print(f"Connection failed: {e}")
            raise

    def home(self, timeout=60000):
        """执行回零操作"""
        if not self.is_connected:
            raise ConnectionError("Device not connected.")
        
        print("Homing stage...")
        try:
            self.device.Home(timeout)
            print("Homing complete.")
        except Exception as e:
            print(f"Homing failed: {e}")

    def get_position(self):
        """获取当前位置 (返回 float)"""
        if not self.is_connected:
            return None
        # .NET Decimal 转 Python float
        return float(str(self.device.Position))

    def move_to(self, position, timeout=60000):
        """
        移动到绝对位置
        :param position: 目标位置 (度或毫米)
        """
        if not self.is_connected:
            raise ConnectionError("Device not connected.")
            
        print(f"Moving to {position}...")
        # 注意：MoveTo 需要 Decimal 类型，但 pythonnet通常能自动处理 float
        try:
            from System import Decimal
            target = Decimal(position)
            self.device.MoveTo(target, timeout)
            print(f"Moved to {position}.")
        except Exception as e:
            print(f"Move failed: {e}")

    def disconnect(self):
        """断开连接并停止轮询"""
        if self.device and self.is_connected:
            print(f"Disconnecting {self.serial_no}...")
            try:
                self.device.StopPolling()
                self.device.Disconnect()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.is_connected = False
                self.device = None
        else:
            print("Device already disconnected or never connected.")

    # --- 上下文管理器支持 (Context Manager) ---
    # 这允许你使用 'with' 语句，自动处理关闭
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()