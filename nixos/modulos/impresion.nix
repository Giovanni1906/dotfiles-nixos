# =============================================================================
# IMPRESION: CUPS, drivers (HP, Brother, Epson, Canon), Avahi y utilidades
# =============================================================================

{ config, pkgs, ... }:

{
  # --------------------------------------------------
  # ---                  Servicios                 ---
  # --------------------------------------------------
  # Servidor de impresión CUPS con soporte de drivers multimarca
  services.printing = {
    enable = true;
    drivers = with pkgs; [
      gutenprint          # Drivers para Canon, Epson y múltiples marcas
      hplip               # Soporte para impresoras y plotters HP (DesignJet, LaserJet, DeskJet)
      brlaser             # Drivers para impresoras Brother
      epson-escpr         # Drivers para impresoras Epson ESC/P-R
      epson-escpr2        # Drivers para modelos Epson más recientes
      canon-cups-ufr2     # Drivers Canon UFR II
      cups-filters        # Filtros de conversión universales (PDF, raster, texto)
    ];
  };

  # Autodescubrimiento de impresoras en red local / Wi-Fi vía mDNS / DNS-SD
  services.avahi = {
    enable = true;
    nssmdns4 = true;
    openFirewall = true;
  };

  # --------------------------------------------------
  # ---                  Paquetes                  ---
  # --------------------------------------------------
  environment.systemPackages = with pkgs; [
    cups                      # Comandos estándar de CUPS (lp, lpstat, lpoptions, cancel)
    system-config-printer     # Interfaz gráfica GTK para añadir o emparejar impresoras en red
    poppler-utils             # Herramientas de inspección PDF (pdfinfo, pdftoppm)
  ];

  # --------------------------------------------------
  # ---                  Aliases                   ---
  # --------------------------------------------------
  environment.shellAliases = {
    imprimir = "~/dotfiles/utils/impresion.sh";
  };
}
