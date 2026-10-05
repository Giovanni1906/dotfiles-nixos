# =============================================================================
# REMOTO: celular (Valent), VPN (Tailscale) y escritorio remoto (WayVNC)
# =============================================================================

{ config, pkgs, ... }:

{
  services.tailscale.enable = true;           # Login: sudo tailscale up (lo hace init.sh)

  # Activar KDE Connect (reemplazado por Valent)
  # programs.kdeconnect.enable = true;

  networking.firewall = {
    # allowedTCPPorts = [ 5900 ];                                # WayVNC en todas las redes (sin contraseña)
    interfaces.tailscale0.allowedTCPPorts = [ 5900 ];            # WayVNC solo por Tailscale
    allowedTCPPortRanges = [ { from = 1714; to = 1764; } ];      # Valent (KDE Connect)
    allowedUDPPortRanges = [ { from = 1714; to = 1764; } ];
  };

  environment.systemPackages = with pkgs; [
    valent                      # Conectar con el celular
    wtype                       # Desbloqueo remoto desde Valent (escribe la contraseña en hyprlock)
    wayvnc                      # Conexión remota desde otro dispositivo
    remmina                     # Cliente de escritorio remoto
  ];

  environment.shellAliases = {
    remote-conexion = "~/dotfiles/utils/wayvnc-tailscale.sh";   # WayVNC solo en la IP de Tailscale
  };
}
