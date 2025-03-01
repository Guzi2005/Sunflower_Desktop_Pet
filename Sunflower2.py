import os
import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import pyaudio
import numpy as np
from scipy.signal import find_peaks, savgol_filter
import time
import sys  # 导入 sys 模块

global_mode = 'B'

class SunflowerDesktopPet:
    def __init__(self, root):
        self.root = root
        self.root.title("Sunflower Desktop Pet")
        # 判断是开发环境还是打包后的环境
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.abspath(__file__))

        image_path = os.path.join(base_path, "Image", "图层-1.png")
        try:
            self.image = Image.open(image_path)
            width, height = self.image.size
            # 适当增大窗口尺寸
            window_width = width + 200
            window_height = height + 200
            self.root.geometry(f"{window_width}x{window_height}") 
            # 隐藏窗口边框和标题栏
            self.root.overrideredirect(True)
            # 设置窗口置顶
            self.root.attributes('-topmost', True)
            self.is_topmost = True  # 记录窗口是否置顶

            # 设置一个特殊的、不太可能出现在图片中的颜色作为透明色
            transparent_color = "#010101"
            self.root.config(bg=transparent_color)
            self.root.attributes('-transparentcolor', transparent_color)

            # 加载图片资源
            images_folder = os.path.join(base_path, "Image")
            self.frames = []
            self.is_fast_forward = False  # 新增快速播放标志

            # 预加载并处理所有图片
            for i in range(1, 26):
                image_name = f"图层-{i}.png"
                image_path = os.path.join(images_folder, image_name)
                if os.path.exists(image_path):
                    image = Image.open(image_path)
                    # resize到原图两倍大
                    resized_image = image.resize((image.width, image.height), Image.Resampling.LANCZOS)
                    self.frames.append(ImageTk.PhotoImage(resized_image))

            # 创建 Canvas 组件
            self.canvas = tk.Canvas(self.root, bg=transparent_color, highlightthickness=0)
            self.canvas.pack()

            # 初始化播放状态
            self.is_playing = True
            self.current_frame = 0
            self.bpm = 60  # 初始化BPM，默认原速
            self.last_valid_bpm = None  # 记录上一次有效的BPM值，初始设为None
            self.total_original_duration = 1000  # 假设所有帧总时长为1000ms，可根据实际调整
            self.update_speed_factor()
            self.update_gif()

            # 事件绑定
            self.canvas.bind("<ButtonPress-1>", self.stop_gif)
            self.canvas.bind("<ButtonRelease-1>", self.start_gif)
            #self.canvas.bind("<Button-1>", self.cycle_speed)
            self.canvas.bind("<Double-Button-1>", self.close_app)
            self.canvas.bind("<ButtonPress-3>", self.on_drag_start)
            self.canvas.bind("<B3-Motion>", self.on_drag_motion)

            # 音频设置
            self.p = pyaudio.PyAudio()
            # 增加每次读取的音频数据量
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=4096)
            self.audio_buffer = []  # 新增音频缓冲区
            self.buffer_size = 3  # 减小缓冲区大小，提高灵敏度

            self.root.after(5, self.analyze_audio)
            self.bpm_history = []  # 新增 BPM 历史记录
            self.history_size = 5  # 历史记录大小
        except FileNotFoundError:
            print(f"Error: Image file not found at {image_path}")

    def update_speed_factor(self):
        """根据BPM计算速度乘数"""
        if self.bpm is not None:
            target_cycle_time = 60000 / self.bpm  # 目标循环时间（毫秒）
            self.speed_factor = target_cycle_time / self.total_original_duration
            # 添加速度因子的限制，避免速度过慢
            self.speed_factor = min(self.speed_factor, 2)  

    def update_gif(self):
        if self.is_playing:
            if self.is_fast_forward:
                frame_delay = 1  # 快速播放
                if global_mode == 'A':
                    print("==========================================拍子==============================================")
                else:
                    print("♿", end="")
                if self.current_frame == len(self.frames) - 1:
                    self.is_fast_forward = False  # 播放完当前循环，取消快速播放
            else:
                frame_delay = int(40 * self.speed_factor)  # 假设每帧默认40ms，可根据实际调整
            self.canvas.delete("all")  # 清除之前的图像
            # 获取窗口尺寸
            window_width = self.canvas.winfo_width()
            window_height = self.canvas.winfo_height()
            # 获取当前帧图片的尺寸
            frame_width = self.frames[self.current_frame].width()
            frame_height = self.frames[self.current_frame].height()
            # 计算图片居中的位置
            fixed_x = (window_width - frame_width) // 2
            fixed_y = (window_height - frame_height) // 2
            self.canvas.create_image(fixed_x, fixed_y, anchor=tk.NW, image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.root.after(max(frame_delay, 2), self.update_gif)

    def cycle_speed(self, event):
        """循环切换播放速度"""
        bpm_options = [45, 60, 90, 120, 150, 180, 240, 360]
        # 将self.bpm转换为最接近的整数
        closest_bpm = min(bpm_options, key=lambda x: abs(x - self.bpm))
        self.bpm = bpm_options[(bpm_options.index(closest_bpm) + 1) % len(bpm_options)]
        self.last_valid_bpm = self.bpm  # 更新上一次有效的BPM值
        self.update_speed_factor()

    def stop_gif(self, event):
        self.is_playing = False

    def start_gif(self, event):
        if not self.is_playing:
            self.is_playing = True
            self.update_gif()

    def on_drag_start(self, event):
        self.drag_data = (event.x_root, event.y_root)

    def on_drag_motion(self, event):
        dx = event.x_root - self.drag_data[0]
        dy = event.y_root - self.drag_data[1]
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")
        self.drag_data = (event.x_root, event.y_root)

    def close_app(self, event):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        self.root.destroy()

    def analyze_audio(self):
        try:
            start_time = time.time()  # 记录开始时间
            data = self.stream.read(4096)
            audio_data = np.frombuffer(data, dtype=np.int16)
            self.audio_buffer.append(audio_data)
            if len(self.audio_buffer) < self.buffer_size:
                self.root.after(5, self.analyze_audio)
                return

            combined_audio = np.concatenate(self.audio_buffer)
            self.audio_buffer = []  # 清空缓冲区

            # 更平滑的滤波处理
            # 修改为较小的 window_length 和 polyorder 值，削弱平滑效果
            audio_data = savgol_filter(combined_audio, window_length=11, polyorder=1)

            # 调整峰值检测参数
            peaks, _ = find_peaks(audio_data, height=300, distance=5)  

            if len(peaks) > 0:
                print("👏")
                # 修改 BPM 计算公式
                total_samples = len(combined_audio)
                total_time = total_samples / 44100  # 总时长（秒）
                bpm = len(peaks) * 60 / total_time / 80
                
                print(f"<实时>BPM: {bpm}")

                # 过滤不合理的 BPM 值
                if 30 < bpm < 300:
                    self.bpm_history.append(bpm)
                    if len(self.bpm_history) > self.history_size:
                        self.bpm_history.pop(0)

                    # 计算平均 BPM
                    average_bpm = np.mean(self.bpm_history)
                    bpm_options = [30, 45, 60, 90, 120, 150, 180, 240, 360, 720, 1080, 2160]
                    closest_bpm = min(bpm_options, key=lambda x: abs(x - average_bpm))
                    self.bpm = closest_bpm
                    self.last_valid_bpm = self.bpm
                    #   self.current_frame = 0
                    self.is_fast_forward = True
                elif self.last_valid_bpm is not None:
                    self.bpm = self.last_valid_bpm
                else:
                    self.bpm = 60

                self.update_speed_factor()

                print(f"    <当前>BPM: {self.bpm}")
            elif self.last_valid_bpm is not None:
                self.bpm = self.last_valid_bpm
                self.update_speed_factor()
                print(f"        <继承>BPM: {self.bpm}")
            else:
                self.bpm = 60
                self.update_speed_factor()
                print(f"            <默认>BPM: {self.bpm}")

            end_time = time.time()  # 记录结束时间
            delay = end_time - start_time  # 计算延迟
            print(f"                                         {delay * 1000:.1f} ms")  # 打印延迟，单位为毫秒

        except Exception as e:
            print(f"<出错>: {e}")
        self.root.after(10, self.analyze_audio)

if __name__ == "__main__":
    root = tk.Tk()
    app = SunflowerDesktopPet(root)
    root.mainloop()
