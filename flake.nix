{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # For python 3.8 compat
    nixpkgs-python.url = "github:cachix/nixpkgs-python";
    flake-parts.url = "github:hercules-ci/flake-parts";
    import-tree.url = "github:vic/import-tree";
    uv2nix.url = "github:Gigahawk/uv2nix/requires-python-test";
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    flake-parts-python = {
      url = "github:Gigahawk/flake-parts-python";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.uv2nix.follows = "uv2nix";
    };
  };

  outputs = inputs: inputs.flake-parts.lib.mkFlake { inherit inputs; } (inputs.import-tree ./modules);
}
