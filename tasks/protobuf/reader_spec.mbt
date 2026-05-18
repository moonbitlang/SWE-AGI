// Copyright 2025 International Digital Economy Academy
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

///|
/// Trait representing the reader
pub(open) trait Reader {
  /// Reads data into the provided buffer, returns the number of bytes read, or None if end of stream
  read(Self, FixedArray[Byte], offset? : Int, max_length? : Int) -> Int? raise
}

///|
pub(open) trait Read {
  read(&Reader) -> Self raise = _
  read_with_limit(LimitedReader[&Reader]) -> Self raise
}

///|
impl Read with read(reader : &Reader) -> Self raise {
  let reader = LimitedReader::new(reader)
  Read::read_with_limit(reader)
}

///|
declare pub type LimitedReader[T]

///|
declare pub fn[T] LimitedReader::new(
  reader : &Reader,
  limit? : Int,
) -> LimitedReader[T]

///|
declare pub type BytesReader

///|
declare pub fn BytesReader::from_bytes(bytes : Bytes) -> BytesReader

///|
declare pub impl[T : Reader] Reader for LimitedReader[T]

///|
declare pub impl Reader for BytesReader

///|
declare pub fn read_tag(reader : &Reader) -> (UInt, UInt) raise

///|
declare pub fn read_varint32(reader : &Reader) -> UInt raise

///|
declare pub fn read_int32(reader : &Reader) -> Int raise

///|
declare pub fn read_int64(reader : &Reader) -> Int64 raise

///|
declare pub fn read_uint32(reader : &Reader) -> UInt raise

///|
declare pub fn read_uint64(reader : &Reader) -> UInt64 raise

///|
declare pub fn read_sint32(reader : &Reader) -> SInt raise

///|
declare pub fn read_sint64(reader : &Reader) -> SInt64 raise

///|
declare pub fn read_fixed32(reader : &Reader) -> UInt raise

///|
declare pub fn read_fixed64(reader : &Reader) -> UInt64 raise

///|
declare pub fn read_sfixed32(reader : &Reader) -> Int raise

///|
declare pub fn read_sfixed64(reader : &Reader) -> Int64 raise

///|
declare pub fn read_float(reader : &Reader) -> Float raise

///|
declare pub fn read_double(reader : &Reader) -> Double raise

///|
declare pub fn read_bool(reader : &Reader) -> Bool raise

///|
declare pub fn read_enum(reader : &Reader) -> Enum raise

///|
declare pub fn read_bytes(reader : &Reader) -> Bytes raise

///|
declare pub fn read_string(reader : &Reader) -> String raise

///|
/// Reads packed repeated field (Array[M])
///
/// Note: packed field are stored as a variable length chunk of data, while regular repeated
/// fields behaves like an iterator, yielding their tag everytime
declare pub fn[M] read_packed(
  reader : &Reader,
  read_fn : (LimitedReader[&Reader]) -> M raise,
  size : UInt?,
) -> Array[M] raise

///|
declare pub fn read_unknown(
  reader : &Reader,
  wire_type : UInt,
) -> Unit raise
