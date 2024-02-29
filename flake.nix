{
  description = "Nix-packages Telegram XP-Bot";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;
    in
    {
      packages.${system} = {
        xp-bot = mkPoetryApplication {
        projectDir = self;
        overrides = defaultPoetryOverrides.extend
        (self: super: {
          editables = super.editables.overridePythonAttrs
          (
            old: {
              buildInputs = (old.buildInputs or [ ]) ++ [ super.flit-core super.setuptools];
            }
          );
        });
        };
        default = self.packages.${system}.xp-bot;
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = [ pkgs.poetry ];
      };

      docker = pkgs.dockerTools.buildLayeredImage {
        name = "xp-bot";
        tag = "latest";
        created = "now";
        config = {
          Cmd = [ "${self.packages.${system}.xp-bot}/bin/xp-bot" ];
          WorkingDir = "/data";
        };
      };
    };
}
