// Copyright 2024 International Digital Economy Academy
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
/// Trait representing the Writer
pub(open) trait Writer {
  write(Self, BytesView) -> Unit raise
}

///|
pub impl Writer for @buffer.Buffer with write(self, bytes : BytesView) raise {
  self.write_bytesview(bytes)
}

///|
declare pub fn write_varint(
  writer : &Writer,
  input : UInt64,
) -> Unit raise

///|
declare pub fn write_tag(
  writer : &Writer,
  tag : (UInt, UInt),
) -> Unit raise

///|
declare pub fn write_int32(writer : &Writer, v : Int) -> Unit raise

///|
declare pub fn write_int64(writer : &Writer, v : Int64) -> Unit raise

///|
declare pub fn write_uint32(writer : &Writer, v : UInt) -> Unit raise

///|
declare pub fn write_uint64(writer : &Writer, v : UInt64) -> Unit raise

///|
declare pub fn write_sint32(writer : &Writer, v : Int) -> Unit raise

///|
declare pub fn write_sint64(writer : &Writer, v : Int64) -> Unit raise

///|
declare pub fn write_fixed32(writer : &Writer, v : UInt) -> Unit raise

///|
declare pub fn write_fixed64(writer : &Writer, v : UInt64) -> Unit raise

///|
declare pub fn write_sfixed32(writer : &Writer, v : Int) -> Unit raise

///|
declare pub fn write_sfixed64(writer : &Writer, v : Int64) -> Unit raise

///|
declare pub fn write_float(writer : &Writer, v : Float) -> Unit raise

///|
declare pub fn write_double(writer : &Writer, v : Double) -> Unit raise

///|
declare pub fn write_bool(writer : &Writer, v : Bool) -> Unit raise

///|
declare pub fn write_enum(writer : &Writer, v : Enum) -> Unit raise

///|
declare pub fn write_bytes(writer : &Writer, v : Bytes) -> Unit raise

///|
declare pub fn write_string(writer : &Writer, v : String) -> Unit raise
