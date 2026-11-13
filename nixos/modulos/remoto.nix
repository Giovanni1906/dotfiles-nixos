# =============================================================================
# REMOTO: celular (Valent), VPN (Tailscale), SSH y escritorio remoto (WayVNC)
# =============================================================================

{ config, pkgs, ... }:

let
  anydeskMirrored = pkgs.anydesk.overrideAttrs (old: {
    src = old.src.overrideAttrs (oldSrc: {
      outputHash =
        if (pkgs.lib.strings.hasPrefix "8.0" (old.version or pkgs.anydesk.version))
        then "sha256-6noMPfe0x6kx/whyd66qcmk7WhEivx3xK5q58Se9Ij0="
        else "sha256-zS5P2eyTHZY7cBW8mQ2Q6M0lXcx9VZZTtpG3Bb6u7IQ=";
      urls = oldSrc.urls ++ [
        "https://web.archive.org/web/20260611112327if_/${builtins.head oldSrc.urls}"
      ];
    });
  });
in
{
  services.tailscale.enable = true;           # Login: sudo tailscale up (lo hace init.sh)

  services.openssh = {
    enable = true;                            # Terminal remota desde el celular (Termux) u otro equipo
    openFirewall = false;                     # No abrir el puerto 22 en la red local; solo por Tailscale
    settings.PermitRootLogin = "no";
  };

  # Activar KDE Connect (reemplazado por Valent)
  # programs.kdeconnect.enable = true;

  networking.firewall = {
    # allowedTCPPorts = [ 5900 ];                                # WayVNC en todas las redes (sin contraseña)
    interfaces.tailscale0.allowedTCPPorts = [ 22 5900 ];         # SSH y WayVNC solo por Tailscale
    allowedTCPPortRanges = [ { from = 1714; to = 1764; } ];      # Valent (KDE Connect)
    allowedUDPPortRanges = [ { from = 1714; to = 1764; } ];
  };

  environment.systemPackages = with pkgs; [
    valent                      # Conectar con el celular
    wtype                       # Desbloqueo remoto desde Valent (escribe la contraseña en hyprlock)
    wayvnc                      # Conexión remota desde otro dispositivo
    remmina                     # Cliente de escritorio remoto
    anydeskMirrored             # Escritorio remoto AnyDesk (respaldo vía Web Archive por 404 upstream)
    tmux                        # Mantener sesiones de terminal vivas por SSH (agy, claude)
  ];

  environment.shellAliases = {
    remote-conexion = "~/dotfiles/utils/wayvnc-tailscale.sh";   # WayVNC solo en la IP de Tailscale
  };
}
