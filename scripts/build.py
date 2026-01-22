import customtkinter
import PyInstaller

ctk_dir = customtkinter.__path__[0]

if __name__ == "__main__":
    print("CustomTkinter is installed at:", ctk_dir)