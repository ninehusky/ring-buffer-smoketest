use ring_buffer_smoketest::collections::queue::Queue;
use ring_buffer_smoketest::collections::ring_buffer::RingBuffer;
use std::hint::black_box;

macro_rules! harness_fn {
    ($name:ident, $body:expr) => {
        fn $name(buf: &mut RingBuffer<i32>) {
            $body(buf);
        }
    };
}

// Define all the wrappers
harness_fn!(call_available_len, |buf: &mut RingBuffer<i32>| {
    black_box(buf.available_len());
});

harness_fn!(call_as_slices, |buf: &mut RingBuffer<i32>| {
    black_box(buf.as_slices());
});

harness_fn!(call_has_elements, |buf: &mut RingBuffer<i32>| {
    black_box(buf.has_elements());
});

harness_fn!(call_is_full, |buf: &mut RingBuffer<i32>| {
    black_box(buf.is_full());
});

harness_fn!(call_len, |buf: &mut RingBuffer<i32>| {
    black_box(buf.len());
});

harness_fn!(call_enqueue, |buf: &mut RingBuffer<i32>| {
    black_box(buf.enqueue(black_box(1)));
});

harness_fn!(call_dequeue, |buf: &mut RingBuffer<i32>| {
    black_box(buf.dequeue());
});

harness_fn!(call_push, |buf: &mut RingBuffer<i32>| {
    black_box(buf.push(black_box(2)));
});

harness_fn!(call_remove_first_matching, |buf: &mut RingBuffer<i32>| {
    let _ = buf.enqueue(3);
    black_box(buf.remove_first_matching(|&x: &i32| x == 3));
});

harness_fn!(call_retain, |buf: &mut RingBuffer<i32>| {
    buf.retain(|&x: &i32| black_box(x) % black_box(2) == 0);
});

harness_fn!(call_empty, |buf: &mut RingBuffer<i32>| {
    buf.empty();
});

#[inline(never)]
fn main() {
    const LEN: usize = 5;
    let mut storage = [0; LEN];
    let mut buf = RingBuffer::new(&mut storage);

    call_available_len(&mut buf);
    call_as_slices(&mut buf);
    call_has_elements(&mut buf);
    call_is_full(&mut buf);
    call_len(&mut buf);
    call_enqueue(&mut buf);
    call_dequeue(&mut buf);
    call_push(&mut buf);
    call_remove_first_matching(&mut buf);
    call_retain(&mut buf);
    call_empty(&mut buf);

    println!("Harness executed all RingBuffer functions at least once.");
}
