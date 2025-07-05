{
  description = "Nix-packages Telegram XP-Bot";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    uv2nix,
    pyproject-nix,
    pyproject-build-systems,
    ...
  }: let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    python = pkgs.python313;
    workspace = uv2nix.lib.workspace.loadWorkspace {
      workspaceRoot = ./.;
    };
    uvLockedOverlay = workspace.mkPyprojectOverlay {
      sourcePreference = "wheel";
    };
    pythonSet = (pkgs.callPackage pyproject-nix.build.packages {inherit python;})
          .overrideScope (nixpkgs.lib.composeManyExtensions [
      pyproject-build-systems.overlays.default
      uvLockedOverlay
    ]);
  in {
    packages.${system} = {
      xp-bot = pythonSet.mkVirtualEnv "xp-bot-env" workspace.deps.default;
      default = self.packages.${system}.xp-bot;
    };

    # devShells.${system}.default = pkgs.mkShell {
    #   packages = [pkgs.poetry];
    # };

    docker = pkgs.dockerTools.buildLayeredImage {
      name = "xp-bot";
      tag = "latest";
      created = "now";
      config = {
        Cmd = ["${self.packages.${system}.xp-bot}/bin/xp-bot"];
        WorkingDir = "/data";
      };
    };
  };
}
