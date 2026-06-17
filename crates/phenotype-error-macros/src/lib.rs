//! Procedural macros for Phenotype error types
//!
//! Provides derive macros for automatically implementing error traits.

use proc_macro::TokenStream;
use quote::quote;

/// Derive macro for `PhenotypeError` trait
#[proc_macro_derive(PhenotypeError)]
pub fn derive_error(input: TokenStream) -> TokenStream {
    let input = proc_macro2::TokenStream::from(input);
    
    // Simple implementation that generates Display and Error traits
    let expanded = quote! {
        // The derive macro implementation
        impl std::fmt::Display for #input {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                write!(f, "{:?}", self)
            }
        }
        
        impl std::error::Error for #input {}
    };
    
    TokenStream::from(expanded)
}
