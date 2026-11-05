# =============================================================================
# DESARROLLO-APPS: desarrollo de aplicaciones (Flutter, móvil Android y Linux desktop)
# =============================================================================
# Agrupa SDKs y herramientas para desarrollo de aplicaciones multiplataforma:
# Flutter SDK, Android Studio con herramientas de emulación, Android tools (adb)
# para conexión con celulares físicos, toolchain de compilación de escritorio Linux
# (CMake, Clang, Ninja, GTK3) y OpenJDK 17.

{ config, pkgs, ... }:

{
  # Aceptar licencias de Android SDK en nixpkgs
  nixpkgs.config.android_sdk.accept_license = true;

  # --------------------------------------------------
  # ---            Paquetes de Desarrollo          ---
  # --------------------------------------------------
  environment.systemPackages = with pkgs; [
    # Flutter & Dart
    flutter                     # SDK de Flutter multiplataforma
    dart                        # Lenguaje Dart y herramientas CLI

    # Móvil (Android) y conexión de celulares
    android-tools               # adb y fastboot para depuración en celular físico por USB/WiFi
    android-studio              # IDE oficial con SDK Manager, emuladores AVD y Logcat
    jdk17                       # OpenJDK 17 requerido por Flutter y Gradle para compilar Android

    # Escritorio (Linux Desktop toolchain para Flutter)
    clang                       # Compilador C/C++ para binarios nativos de escritorio
    cmake                       # Generador de proyectos requerido por Flutter Linux
    ninja                       # Sistema de compilación rápido
    pkg-config                  # Detección de bibliotecas GTK/GLib en tiempo de compilación
    gtk3                        # Biblioteca de interfaz gráfica para apps Linux nativas
    glib                        # Biblioteca base de bajo nivel para GTK3

    # Navegador para depuración Web en Flutter
    chromium                    # Navegador compatible con la toolchain web de Flutter
  ];

  # --------------------------------------------------
  # ---          Variables de Entorno Globales     ---
  # --------------------------------------------------
  environment.variables = {
    # Java JDK para Gradle y compilaciones de Android
    JAVA_HOME = "${pkgs.jdk17.home}";

    # Ruta por defecto del SDK de Android instalado por Android Studio
    ANDROID_HOME = "/home/${config.dotfiles.usuario}/Android/Sdk";
    ANDROID_SDK_ROOT = "/home/${config.dotfiles.usuario}/Android/Sdk";

    # Ejecutable de navegador para flutter run -d chrome / web
    CHROME_EXECUTABLE = "${pkgs.chromium}/bin/chromium";
  };

  # --------------------------------------------------
  # ---              Atajos de Shell               ---
  # --------------------------------------------------
  environment.shellAliases = {
    adb-devices    = "adb devices -l";
    adb-tcpip      = "adb tcpip 5555";
    flutter-doctor = "flutter doctor -v";
  };
}
