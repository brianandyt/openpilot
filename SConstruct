import os
import shutil
import subprocess
import sys
import sysconfig
import platform
import numpy as np

TICI = os.path.isfile('/TICI')
Decider('MD5-timestamp')

AddOption('--test',
          action='store_true',
          help='build test files')

AddOption('--asan',
          action='store_true',
          help='turn on ASAN')

AddOption('--clazy',
          action='store_true',
          help='build with clazy')

real_arch = arch = subprocess.check_output(["uname", "-m"], encoding='utf8').rstrip()
if platform.system() == "Darwin":
  arch = "Darwin"

if arch == "aarch64" and TICI:
  arch = "larch64"

USE_WEBCAM = os.getenv("USE_WEBCAM") is not None
QCOM_REPLAY = arch == "aarch64" and os.getenv("QCOM_REPLAY") is not None

if arch == "aarch64" or arch == "larch64":
  lenv = {
    "LD_LIBRARY_PATH": '/data/data/com.termux/files/usr/lib',
    "PATH": os.environ['PATH'],
  }

  if arch == "aarch64":
    # android
    lenv["ANDROID_DATA"] = os.environ['ANDROID_DATA']
    lenv["ANDROID_ROOT"] = os.environ['ANDROID_ROOT']

  cpppath = [
    "#phonelibs/opencl/include",
  ]

  libpath = [
    "/usr/lib",
    "/system/vendor/lib64",
    "/system/comma/usr/lib",
    "#phonelibs/nanovg",
  ]

  if arch == "larch64":
    libpath += [
      "#phonelibs/snpe/larch64",
      "#phonelibs/libyuv/larch64/lib",
      "/usr/lib/aarch64-linux-gnu"
    ]
    cflags = ["-DQCOM2", "-mcpu=cortex-a57"]
    cxxflags = ["-DQCOM2", "-mcpu=cortex-a57"]
    rpath = ["/usr/local/lib"]
  else:
    libpath += [
      "#phonelibs/snpe/aarch64",
      "#phonelibs/libyuv/lib",
      "/system/vendor/lib64"
    ]
    cflags = ["-DQCOM", "-mcpu=cortex-a57"]
    cxxflags = ["-DQCOM", "-mcpu=cortex-a57"]
    rpath = []

    if QCOM_REPLAY:
      cflags += ["-DQCOM_REPLAY"]
      cxxflags += ["-DQCOM_REPLAY"]
else:
  cflags = []
  cxxflags = []

  lenv = {
    "PATH": "#external/bin:" + os.environ['PATH'],
  }
  cpppath = [
    "#external/tensorflow/include",
  ]

  if arch == "Darwin":
    libpath = [
      "#phonelibs/libyuv/mac/lib",
      "#cereal",
      "#selfdrive/common",
      "/usr/local/lib",
      "/usr/local/opt/openssl/lib",
      "/System/Library/Frameworks/OpenGL.framework/Libraries",
    ]
    cflags += ["-DGL_SILENCE_DEPRECATION"]
    cxxflags += ["-DGL_SILENCE_DEPRECATION"]
    cpppath += ["/usr/local/opt/openssl/include"]
  else:
    libpath = [
      "#phonelibs/snpe/x86_64-linux-clang",
      "#phonelibs/libyuv/x64/lib",
      "#external/tensorflow/lib",
      "#cereal",
      "#selfdrive/common",
      "/usr/lib",
      "/usr/local/lib",
    ]

  rpath = [
    "phonelibs/snpe/x86_64-linux-clang",
    "external/tensorflow/lib",
    "cereal",
    "selfdrive/common"
  ]

  # allows shared libraries to work globally
  rpath = [os.path.join(os.getcwd(), x) for x in rpath]

if GetOption('asan'):
  ccflags_asan = ["-fsanitize=address", "-fno-omit-frame-pointer"]
  ldflags_asan = ["-fsanitize=address"]
else:
  ccflags_asan = []
  ldflags_asan = []

# change pythonpath to this
lenv["PYTHONPATH"] = Dir("#").path

env = Environment(
  ENV=lenv,
  CCFLAGS=[
    "-g",
    "-fPIC",
    "-O2",
    "-Wunused",
    "-Werror",
    "-Wno-unknown-warning-option",
    "-Wno-deprecated-register",
    "-Wno-register",
    "-Wno-inconsistent-missing-override",
    "-Wno-c99-designator",
    "-Wno-reorder-init-list",
  ] + cflags + ccflags_asan,

  CPPPATH=cpppath + [
    "#",
    "#selfdrive",
    "#phonelibs/bzip2",
    "#phonelibs/libyuv/include",
    "#phonelibs/openmax/include",
    "#phonelibs/json11",
    "#phonelibs/curl/include",
    "#phonelibs/libgralloc/include",
    "#phonelibs/android_frameworks_native/include",
    "#phonelibs/android_hardware_libhardware/include",
    "#phonelibs/android_system_core/include",
    "#phonelibs/linux/include",
    "#phonelibs/snpe/include",
    "#phonelibs/nanovg",
    "#selfdrive/boardd",
    "#selfdrive/common",
    "#selfdrive/camerad",
    "#selfdrive/camerad/include",
    "#selfdrive/loggerd/include",
    "#selfdrive/modeld",
    "#selfdrive/sensord",
    "#selfdrive/ui",
    "#cereal/messaging",
    "#cereal",
    "#opendbc/can",
  ],

  CC='clang',
  CXX='clang++',
  LINKFLAGS=ldflags_asan,

  RPATH=rpath,

  CFLAGS=["-std=gnu11"] + cflags,
  CXXFLAGS=["-std=c++1z"] + cxxflags,
  LIBPATH=libpath + [
    "#cereal",
    "#phonelibs",
    "#opendbc/can",
    "#selfdrive/boardd",
    "#selfdrive/common",
  ],
  CYTHONCFILESUFFIX=".cpp",
  COMPILATIONDB_USE_ABSPATH=True,
  tools=["default", "cython", "compilation_db"],
)

if GetOption('test'):
  env.CompilationDatabase('compile_commands.json')

if os.environ.get('SCONS_CACHE'):
  cache_dir = '/tmp/scons_cache'
  if TICI:
    cache_dir = '/data/scons_cache'

  if QCOM_REPLAY:
    cache_dir = '/tmp/scons_cache_qcom_replay'

  CacheDir(cache_dir)

node_interval = 5
node_count = 0
def progress_function(node):
  global node_count
  node_count += node_interval
  sys.stderr.write("progress: %d\n" % node_count)

if os.environ.get('SCONS_PROGRESS'):
  Progress(progress_function, interval=node_interval)

SHARED = False

def abspath(x):
  if arch == 'aarch64':
    pth = os.path.join("/data/pythonpath", x[0].path)
    env.Depends(pth, x)
    return File(pth)
  else:
    # rpath works elsewhere
    return x[0].path.rsplit("/", 1)[1][:-3]

# Cython build enviroment
py_include = sysconfig.get_paths()['include']
envCython = env.Clone()
envCython["CPPPATH"] += [py_include, np.get_include()]
envCython["CCFLAGS"] += ["-Wno-#warnings", "-Wno-deprecated-declarations"]

envCython["LIBS"] = []
if arch == "Darwin":
  envCython["LINKFLAGS"] = ["-bundle", "-undefined", "dynamic_lookup"]
elif arch == "aarch64":
  envCython["LINKFLAGS"] = ["-shared"]
  envCython["LIBS"] = [os.path.basename(py_include)]
else:
  envCython["LINKFLAGS"] = ["-pthread", "-shared"]

Export('envCython')

# Qt build environment
qt_env = None
if arch in ["x86_64", "Darwin", "larch64"]:
  qt_env = env.Clone()

  qt_modules = ["Widgets", "Gui", "Qml", "Quick", "Core", "DBus", "Location", "Multimedia", "Network", "Positioning"]

  qt_libs = []
  if arch == "Darwin":
    qt_env['QTDIR'] = "/usr/local/opt/qt"
    QT_BASE = "/usr/local/opt/qt/"
    qt_dirs = [
      QT_BASE + "include/",
    ]
    qt_dirs += [f"{QT_BASE}include/Qt{m}" for m in qt_modules]
    qt_env["LINKFLAGS"] += ["-F" + QT_BASE + "lib"]
    qt_env["FRAMEWORKS"] += [f"Qt{m}" for m in qt_modules] + ["OpenGL"]
  else:
    QT_BASE = f"/usr/include/{real_arch}-linux-gnu/qt5"
    qt_env['QTDIR'] = "/usr"
    qt_dirs = [
      f"{QT_BASE}",
    ]
    qt_dirs += [f"{QT_BASE}/Qt{m}" for m in qt_modules]

    qt_libs = [f"Qt5{m}" for m in qt_modules]
    if arch == "larch64":
      qt_libs += ["GLESv2", "wayland-client"]
    elif arch != "Darwin":
      qt_libs += ["GL"]

  qt_env.Tool('qt')
  qt_env['CPPPATH'] += qt_dirs + ["#selfdrive/ui/qt/"]
  qt_flags = [
    "-D_REENTRANT",
    "-DQT_NO_DEBUG",
    "-DQT_WIDGETS_LIB",
    "-DQT_GUI_LIB",
    "-DQT_CORE_LIB"
  ]
  qt_env['CXXFLAGS'] += qt_flags
  qt_env['LIBPATH'] += ['#selfdrive/ui']
  qt_env['LIBS'] = qt_libs

  if GetOption("clazy"):
    checks = [
      "level0",
      "level1",
      "no-range-loop",
      "no-non-pod-global-static",
    ]
    qt_env['CXX'] = 'clazy'
    qt_env['ENV']['CLAZY_IGNORE_DIRS'] = qt_dirs[0]
    qt_env['ENV']['CLAZY_CHECKS'] = ','.join(checks)
Export('qt_env')


# still needed for apks
zmq = 'zmq'
Export('env', 'arch', 'real_arch', 'zmq', 'SHARED', 'USE_WEBCAM', 'QCOM_REPLAY')

# cereal and messaging are shared with the system
SConscript(['cereal/SConscript'])
if SHARED:
  cereal = abspath([File('cereal/libcereal_shared.so')])
  messaging = abspath([File('cereal/libmessaging_shared.so')])
else:
  cereal = [File('#cereal/libcereal.a')]
  messaging = [File('#cereal/libmessaging.a')]
Export('cereal', 'messaging')

SConscript(['selfdrive/common/SConscript'])
Import('_common', '_visionipc', '_gpucommon', '_gpu_libs')

if SHARED:
  common, visionipc, gpucommon = abspath(common), abspath(visionipc), abspath(gpucommon)
else:
  common = [_common, 'json11']
  visionipc = _visionipc
  gpucommon = [_gpucommon] + _gpu_libs

Export('common', 'visionipc', 'gpucommon')


# Build openpilot

SConscript(['cereal/SConscript'])
SConscript(['opendbc/can/SConscript'])

SConscript(['phonelibs/SConscript'])

SConscript(['common/SConscript'])
SConscript(['common/kalman/SConscript'])
SConscript(['common/transformations/SConscript'])

SConscript(['selfdrive/camerad/SConscript'])
SConscript(['selfdrive/modeld/SConscript'])

SConscript(['selfdrive/controls/lib/cluster/SConscript'])
SConscript(['selfdrive/controls/lib/lateral_mpc/SConscript'])
SConscript(['selfdrive/controls/lib/longitudinal_mpc/SConscript'])
SConscript(['selfdrive/controls/lib/longitudinal_mpc_model/SConscript'])

SConscript(['selfdrive/boardd/SConscript'])
SConscript(['selfdrive/proclogd/SConscript'])
SConscript(['selfdrive/clocksd/SConscript'])

SConscript(['selfdrive/loggerd/SConscript'])

SConscript(['selfdrive/locationd/SConscript'])
SConscript(['selfdrive/locationd/models/SConscript'])
SConscript(['selfdrive/sensord/SConscript'])
SConscript(['selfdrive/ui/SConscript'])

if arch != "Darwin":
  SConscript(['selfdrive/logcatd/SConscript'])

if real_arch == "x86_64":
  SConscript(['tools/nui/SConscript'])
  SConscript(['tools/lib/index_log/SConscript'])
