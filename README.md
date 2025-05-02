# Elecraft-P3-Windows-Interface
This application provides point-and-click / scroll-wheel control of frequency and span. 
This application was designed for Windows for use with the [Elecraft P3](https://ftp.elecraft.com/P3/Manuals%20Downloads/E740152%20P3%20Owner%27s%20man%20Rev%20H1.pdf) with the [SVG add-on](https://ftp.elecraft.com/P3/Manuals%20Downloads/E740170%20P3%20SVGA%20Option%20Rev%20E.pdf) and a video capture device [like this one](https://a.co/d/1YxC9fZ).

![image](https://github.com/user-attachments/assets/fd18076d-d2c3-4bf0-b7ea-f47cfe36f065)

This script was a co-development with ChatGPT. It can be compiled into an executable by:

    pip install pyinstaller  
    pyinstaller --onefile --windowed K3_P3.py


  This will create:
>       dist/
>           K3_P3.exe
>       build/
>           (temporary build files)
>       K3_P3.spec

      
Your executable will be in the _**dist folder**_.

 - Select video source, comm port and baudrate that is compatible with your setup and click 'Save'     
 - Span selections are 10K, 50K, 100K, and 200K.     
 - Click in the spectrum or waterfall to change the center frequency.        
 - Roll the mouse-wheel up and down to move the center frequency in small amounts.

73,
WR9R
