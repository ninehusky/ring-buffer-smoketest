#![no_std]
// use flux_rs::attrs::*;
extern crate flux_core;

#[cfg_attr(flux, flux::no_panic)]
pub mod collections;

// #[flux::spec(fn(x: i32) -> i32{v: x < v})]
// fn inc(x: i32) -> i32 {
//     x + 1
// }
