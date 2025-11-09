{
  description = "Market Maker App - Python project with Nix flake dev shell";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonEnv = pkgs.python312.withPackages (ps: [
          ps.sqlalchemy
          ps.python-dotenv
        ]);
      in
      {
        packages.default = pythonEnv;

        devShells.default = pkgs.mkShell {
          buildInputs = [
            (pkgs.python312.withPackages (ps: [
              ps.sqlalchemy
              ps.python-dotenv
              ps.pytest
              ps.fastapi
              ps.uvicorn
              ps.pyyaml
              ps.pip
            ]))
          ];
          
          shellHook = ''
            echo "Market Maker App development environment"
            echo "Python: $(python --version)"
            echo "Available packages: sqlalchemy, python-dotenv, pytest, fastapi, uvicorn"
            echo "Run tests with: pytest tests/"
            echo "Run API server with: python main.py"
          '';
        };
      }
    );
}

