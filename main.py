from PIL import Image, ImageTk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, colorchooser, messagebox

MEMORY_SIZE = 4096

def disassemble(opcode: int) -> str:
    nnn = opcode & 0x0FFF
    n   = opcode & 0x000F
    x   = (opcode & 0x0F00) >> 8
    y   = (opcode & 0x00F0) >> 4
    kk  = opcode & 0x00FF
    if opcode == 0x00E0:
        return "CLS"
    elif opcode == 0x00EE:
        return "RET"
    elif opcode & 0xF000 == 0x1000:
        return f"JP {nnn:03X}"
    elif opcode & 0xF000 == 0x2000:
        return f"CALL {nnn:03X}"
    elif opcode & 0xF000 == 0x3000:
        return f"SE V{x:X}, {kk:02X}"
    elif opcode & 0xF000 == 0x4000:
        return f"SNE V{x:X}, {kk:02X}"
    elif opcode & 0xF000 == 0x5000 and n == 0:
        return f"SE V{x:X}, V{y:X}"
    elif opcode & 0xF000 == 0x6000:
        return f"LD V{x:X}, {kk:02X}"
    elif opcode & 0xF000 == 0x7000:
        return f"ADD V{x:X}, {kk:02X}"
    elif opcode & 0xF000 == 0x8000:
        if n == 0x0: return f"LD V{x:X}, V{y:X}"
        if n == 0x1: return f"OR V{x:X}, V{y:X}"
        if n == 0x2: return f"AND V{x:X}, V{y:X}"
        if n == 0x3: return f"XOR V{x:X}, V{y:X}"
        if n == 0x4: return f"ADD V{x:X}, V{y:X}"
        if n == 0x5: return f"SUB V{x:X}, V{y:X}"
        if n == 0x6: return f"SHR V{x:X}"
        if n == 0x7: return f"SUBN V{x:X}, V{y:X}"
        if n == 0xE: return f"SHL V{x:X}"
    elif opcode & 0xF000 == 0x9000 and n == 0:
        return f"SNE V{x:X}, V{y:X}"
    elif opcode & 0xF000 == 0xA000:
        return f"LD I, {nnn:03X}"
    elif opcode & 0xF000 == 0xB000:
        return f"JP V0, {nnn:03X}"
    elif opcode & 0xF000 == 0xC000:
        return f"RND V{x:X}, {kk:02X}"
    elif opcode & 0xF000 == 0xD000:
        return f"DRW V{x:X}, V{y:X}, {n:X}"
    elif opcode & 0xF000 == 0xE000:
        if kk == 0x9E: return f"SKP V{x:X}"
        if kk == 0xA1: return f"SKNP V{x:X}"
    elif opcode & 0xF000 == 0xF000:
        if kk == 0x07: return f"LD V{x:X}, DT"
        if kk == 0x0A: return f"LD V{x:X}, K"
        if kk == 0x15: return f"LD DT, V{x:X}"
        if kk == 0x18: return f"LD ST, V{x:X}"
        if kk == 0x1E: return f"ADD I, V{x:X}"
        if kk == 0x29: return f"LD F, V{x:X}"
        if kk == 0x33: return f"LD B, V{x:X}"
        if kk == 0x55: return f"LD [I], V0-V{x:X}"
        if kk == 0x65: return f"LD V0-V{x:X}, [I]"
    return f"UNKNOWN {opcode:04X}"

# Chip-8 core
class Chip8:
    def __init__(self):
        # 4 kb of memory
        self.memory = [0] * MEMORY_SIZE

        # Registers
        self.V = [0] * 16

        # Index register and program counter
        self.I = 0
        self.pc = 0x200 # Starts at 512
        
        # Stores return addresses for subroutines
        self.stack = []
        
        # Timers
        self.delay_timer = 0
        self.sound_timer = 0
        
        # 64x32 Monochrome display
        self.display = [[0] * 64 for _ in range(32)]

        # Chip-8 has 16 keys
        self.keys = [0] * 16
        
        # Load fontset to memory
        fontset = [
            0xF0,0x90,0x90,0x90,0xF0, # 0
            0x20,0x60,0x20,0x20,0x70, # 1
            0xF0,0x10,0xF0,0x80,0xF0, # 2
            0xF0,0x10,0xF0,0x10,0xF0, # 3
            0x90,0x90,0xF0,0x10,0x10, # 4
            0xF0,0x80,0xF0,0x10,0xF0, # 5
            0xF0,0x80,0xF0,0x90,0xF0, # 6
            0xF0,0x10,0x20,0x40,0x40, # 7
            0xF0,0x90,0xF0,0x90,0xF0, # 8
            0xF0,0x90,0xF0,0x10,0xF0, # 9
            0xF0,0x90,0xF0,0x90,0x90, # A
            0xE0,0x90,0xE0,0x90,0xE0, # B
            0xF0,0x80,0x80,0x80,0xF0, # C
            0xE0,0x90,0x90,0x90,0xE0, # D
            0xF0,0x80,0xF0,0x80,0xF0, # E
            0xF0,0x80,0xF0,0x80,0x80  # F
        ]
        for i in range(len(fontset)):
            self.memory[i] = fontset[i]
    
    def load_rom(self, path):
        with open(path, "rb") as f:
            rom = f.read()
        for i, byte in enumerate(rom):
            self.memory[0x200 + i] = byte

    def cycle(self):
        # Fetch
        opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]
        self.pc += 2 # Since one Chip-8 instruction is 2 bytes

        # Decode
        nnn = opcode & 0x0FFF # Address
        n = opcode & 0x000F # Least significant nibble
        x = (opcode & 0x0F00) >> 8 # Register X
        y = (opcode & 0x00F0) >> 4 # Register Y
        kk = opcode & 0x00FF # The byte

        # Execute
        if opcode == 0x00E0:
            # CLS
            self.display = [[0] * 64 for _ in range(32)]
        elif opcode == 0x00EE:
            # RET
            self.pc = self.stack.pop()
        elif opcode & 0xF000 == 0x0000:
            # Ignored
            pass
        elif opcode & 0xF000 == 0x1000:
            # JP addr
            self.pc = nnn
        elif opcode & 0xF000 == 0x2000:
            # CALL addr
            self.stack.append(self.pc)
            self.pc = nnn
        elif opcode & 0xF000 == 0x3000:
            # SE Vx, byte
            if self.V[x] == kk:
                self.pc += 2
        elif opcode & 0xF000 == 0x4000:
            # SNE Vx, byte
            if self.V[x] != kk:
                self.pc += 2
        elif opcode & 0xF000 == 0x5000:
            # SE Vx, Vy
            if n == 0 and self.V[x] == self.V[y]:
                self.pc += 2
        elif opcode & 0xF000 == 0x6000:
            # LD Vx, byte
            self.V[x] = kk
        elif opcode & 0xF000 == 0x7000:
            # ADD Vx, byte
            self.V[x] = (self.V[x] + kk) & 0xFF
        elif opcode & 0xF000 == 0x8000:
            if n == 0x0:
                # LD Vx, Vy
                self.V[x] = self.V[y]
            elif n == 0x1:
                # OR Vx, Vy
                self.V[x] |= self.V[y]
            elif n == 0x2:
                # AND Vx, Vy
                self.V[x] &= self.V[y]
            elif n == 0x3:
                # XOR Vx, Vy
                self.V[x] ^= self.V[y]
            elif n == 0x4:
                # ADD Vx, Vy
                result = self.V[x] + self.V[y]
                self.V[0xF] = 1 if result > 0xFF else 0
                self.V[x] = result & 0xFF
            elif n == 0x5:
                # SUB Vx, Vy
                self.V[0xF] = 1 if self.V[x] > self.V[y] else 0
                self.V[x] = (self.V[x] - self.V[y]) & 0xFF
            elif n == 0x6:
                # SHR Vx {, Vy}
                self.V[0xF] = self.V[x] & 0x1
                self.V[x] >>= 1
            elif n == 0x7:
                # SUBN Vx, Vy
                self.V[0xF] = 1 if self.V[y] > self.V[x] else 0
                self.V[x] = (self.V[y] - self.V[x]) & 0xFF
            elif n == 0xE:
                # SHL Vx {, Vy}
                self.V[0xF] = (self.V[x] & 0x80) >> 7
                self.V[x] = (self.V[x] << 1) & 0xFF
        elif opcode & 0xF000 == 0x9000:
            # SNE Vx, Vy
            if n == 0 and self.V[x] != self.V[y]:
                self.pc += 2
        elif opcode & 0xF000 == 0xA000:
            # LD I, addr
            self.I = nnn
        elif opcode & 0xF000 == 0xB000:
            # JP V0, addr
            self.pc = nnn + self.V[0]
        elif opcode & 0xF000 == 0xC000:
            # RND Vx, byte
            import random
            self.V[x] = random.randint(0, 255) & kk
        elif opcode & 0xF000 == 0xD000:
            # DRW Vx, Vy, nibble
            vx, vy = self.V[x], self.V[y]
            self.V[0xF] = 0
            for row in range(n):
                sprite = self.memory[self.I + row]
                for col in range(8):
                    if (sprite & (0x80 >> col)) != 0:
                        px = (vx + col) % 64
                        py = (vy + row) % 32
                        if self.display[py][px] == 1:
                            self.V[0xF] = 1
                        self.display[py][px] ^= 1
        elif opcode & 0xF000 == 0xE000:
            if kk == 0x9E:
                # SKP Vx
                if self.keys[self.V[x]] == 1:
                    self.pc += 2
            elif kk == 0xA1:
                # SKNP Vx
                if self.keys[self.V[x]] == 0:
                    self.pc += 2
        elif opcode & 0xF000 == 0xF000:
            if kk == 0x07:
                # LD Vx, DT
                self.V[x] = self.delay_timer
            elif kk == 0x0A:
                # LD Vx, K
                pressed = None
                for i in range(16):
                    if self.keys[i]:
                        pressed = i
                        break
                if pressed is None:
                    self.pc -= 2 # repeat this instruction until key pressed
                else:
                    self.V[x] = pressed
            elif kk == 0x15:
                # LD DT, Vx
                self.delay_timer = self.V[x]
            elif kk == 0x18:
                # LD ST, Vx
                self.sound_timer = self.V[x]
            elif kk == 0x1E:
                # ADD I, Vx
                self.I = (self.I + self.V[x]) & 0xFFF
            elif kk == 0x29:
                # LD F, Vx (sprite addr for digit)
                self.I = self.V[x] * 5
            elif kk == 0x33:
                # LD B, Vx (BCD)
                value = self.V[x]
                self.memory[self.I]     = value // 100
                self.memory[self.I + 1] = (value // 10) % 10
                self.memory[self.I + 2] = value % 10
            elif kk == 0x55:
                # LD [I], V0..Vx
                for i in range(x + 1):
                    self.memory[self.I + i] = self.V[i]
            elif kk == 0x65:
                # LD V0..Vx, [I]
                for i in range(x + 1):
                    self.V[i] = self.memory[self.I + i]

        else:
            raise Exception(f"Unknown opcode {opcode:04X}")

# Tkinter screen component
class Screen:
    def __init__(self,parent,chip8,scale=10):
        self.chip8=chip8
        self.scale=scale
        self.width=64
        self.height=32
        self.fg_color=(255,255,255)
        self.bg_color=(0,0,0)
        self.image=Image.new("RGB",(self.width,self.height),"black")
        self.photo=ImageTk.PhotoImage(self.image.resize((self.width*scale,self.height*scale),Image.NEAREST))
        self.label=ttk.Label(parent,image=self.photo)
        self.label.pack()

    def draw(self):
        pixels=self.image.load()
        for y in range(self.height):
            for x in range(self.width):
                pixels[x,y]=self.fg_color if self.chip8.display[y][x] else self.bg_color
        self.photo=ImageTk.PhotoImage(self.image.resize((self.width*self.scale,self.height*self.scale),Image.NEAREST))
        self.label.config(image=self.photo)
        self.label.image=self.photo

    def set_colors(self,fg,bg):
        self.fg_color=fg
        self.bg_color=bg

# Main app
class App:
    def __init__(self,root):
        self.root=root
        self.root.title("Chip-8 Emulator")
        self.chip8=None
        self.running=False

        self.keymap={"x":0x0,"1":0x1,"2":0x2,"3":0x3,"q":0x4,"w":0x5,"e":0x6,"a":0x7,
                     "s":0x8,"d":0x9,"z":0xA,"c":0xB,"4":0xC,"r":0xD,"f":0xE,"v":0xF}

        root.bind("<KeyPress>",self.key_press)
        root.bind("<KeyRelease>",self.key_release)

        # Screen frame
        self.screen_frame=ttk.Frame(root)
        self.screen_frame.pack(pady=10)
        self.screen=None

        # Controls
        self.control_frame=ttk.Frame(root)
        self.control_frame.pack(pady=5)
        ttk.Button(self.control_frame,text="Load ROM",command=self.load_rom,bootstyle=SUCCESS).grid(row=0,column=0,padx=5)
        self.run_button=ttk.Button(self.control_frame,text="Run",command=self.toggle_run,bootstyle=PRIMARY,state=DISABLED)
        self.run_button.grid(row=0,column=1,padx=5)
        self.pause_button=ttk.Button(self.control_frame,text="Pause",command=self.pause,bootstyle=DANGER,state=DISABLED)
        self.pause_button.grid(row=0,column=2,padx=5)
        ttk.Button(self.control_frame,text="Set Colors",command=self.set_colors,bootstyle=INFO).grid(row=0,column=3,padx=5)
        ttk.Button(self.control_frame, text="Key Bindings", command=self.edit_key_bindings).grid(row=0, column=4, padx=5)
        self.disassemble_button = ttk.Button(self.control_frame, text="Disassemble", command=self.disassemble, state=DISABLED)
        self.disassemble_button.grid(row=0, column=5, padx=5)
        self.update_loop()

    def key_press(self,event):
        if self.chip8:
            key=event.char.lower()
            if key in self.keymap: self.chip8.keys[self.keymap[key]]=1

    def key_release(self,event):
        if self.chip8:
            key=event.char.lower()
            if key in self.keymap: self.chip8.keys[self.keymap[key]]=0

    def load_rom(self):
        filepath=filedialog.askopenfilename(filetypes=[("Chip-8 ROM","*.ch8")])
        if filepath:
            with open(filepath, "rb") as f:
                rom = f.read()

            if len(rom) > (MEMORY_SIZE - 0x200):
                messagebox.showerror("Error", "ROM file is too large for Chip-8 memory!")
                return

            self.chip8=Chip8()
            self.chip8.load_rom(filepath)
            if self.screen is None:
                self.screen=Screen(self.screen_frame,self.chip8,scale=10)
            else:
                self.screen.chip8=self.chip8
            self.run_button.config(state=NORMAL)
            self.disassemble_button.config(state=NORMAL)

    def toggle_run(self):
        self.running = not self.running
        self.run_button.config(state=DISABLED)
        self.pause_button.config(state=NORMAL)

    def pause(self):
        self.running=False
        self.pause_button.config(state=DISABLED)
        self.run_button.config(state=NORMAL)

    def set_colors(self):
        fg=colorchooser.askcolor(title="Select foreground color")[0]
        bg=colorchooser.askcolor(title="Select background color")[0]
        if fg and bg:
            fg_rgb=tuple(map(int,fg))
            bg_rgb=tuple(map(int,bg))
            if self.screen: self.screen.set_colors(fg_rgb,bg_rgb)

    def edit_key_bindings(self):
        if not self.chip8:
            return

        win = ttk.Toplevel(self.root)
        win.title("Edit Key Bindings")

        instructions = ttk.Label(win, text="Click a Chip-8 key, then press the new keyboard key")
        instructions.pack(pady=5)

        frame = ttk.Frame(win)
        frame.pack(padx=10, pady=10)

        # Display current key mappings
        for i in range(16):
            chip8_key = f"{i:X}"
            btn = ttk.Button(frame, text=f"{chip8_key}: {self.get_key_for_chip8(i)}", width=15)
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)

            # Bind click
            btn.bind("<Button-1>", lambda e, key=i, b=btn: self.wait_for_key(win, key, b))

    def disassemble(self):
        if not self.chip8:
            return
        
        win = ttk.Toplevel(self.root)
        win.title("Disassemble")

        asm_viewer = ttk.Text(win, wrap="none")
        asm_viewer.pack(fill="both", expand=True)
        
        pc = 0x200
        while pc < MEMORY_SIZE - 1:
            opcode = (self.chip8.memory[pc] << 8) | self.chip8.memory[pc+1]
            asm = disassemble(opcode)
            asm_viewer.insert("end", f"{pc:03X}: {opcode:004X}   {asm}\n")
            pc += 2
        asm_viewer.config(state="disabled")

    def get_key_for_chip8(self, chip8_index):
        for k, v in self.keymap.items():
            if v == chip8_index:
                return k
        return "?"

    def wait_for_key(self, window, chip8_key, button):
        def on_press(event):
            key = event.keysym.lower()
            # Update keymap
            self.keymap[key] = chip8_key
            button.config(text=f"{chip8_key:X}: {key}")
            window.unbind("<KeyPress>", bind_id)

        bind_id = window.bind("<KeyPress>", on_press)
    
    def update_loop(self):
        if self.chip8 and self.running:
            for _ in range(10):
                self.chip8.cycle()
            if self.screen: self.screen.draw()
        self.root.after(16,self.update_loop)

if __name__=="__main__":
    root=ttk.Window(themename="darkly")
    app=App(root)
    root.mainloop()