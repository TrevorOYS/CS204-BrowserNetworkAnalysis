{
  description = "BrowserBench development shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
          browserRuntimeLibs = with pkgs; [
            alsa-lib
            atk
            at-spi2-atk
            cairo
            cups
            dbus
            expat
            fontconfig
            freetype
            gdk-pixbuf
            glib
            gtk3
            libdrm
            libgbm
            libxkbcommon
            mesa
            nspr
            nss
            pango
            stdenv.cc.cc.lib
            wayland
            libx11
            libxscrnsaver
            libxcomposite
            libxcursor
            libxdamage
            libxext
            libxfixes
            libxi
            libxrandr
            libxrender
            libxcb
            libxshmfence
          ];
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python313
              python313Packages.pip
              uv
              nodejs_24
            ] ++ browserRuntimeLibs;

            shellHook = ''
              export PLAYWRIGHT_NODEJS_PATH="${pkgs.nodejs_24}/bin/node"
              export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath browserRuntimeLibs}:''${LD_LIBRARY_PATH:-}"
              echo "BrowserBench dev shell ready."
              echo "PLAYWRIGHT_NODEJS_PATH=$PLAYWRIGHT_NODEJS_PATH"
            '';
          };
        });
    };
}
