// Minimal CoreAudio default-device tool. Compiled and cached by `audio-route`.
//
// macOS ships no CLI for reading or setting the default input and output
// device — `SwitchAudioSource` is the usual answer, but that is a Homebrew
// install to do what is four CoreAudio properties. This is those four.
//
//   audiodev list in|out         uid<TAB>name, one device per line
//   audiodev get  in|out         uid<TAB>name of the current default
//   audiodev set  in|out <spec>  spec is a device UID, or an exact name,
//                                or a case-insensitive substring of one
//
// Exit 0 on success, 1 on a bad argument, 2 when a device cannot be found or
// the set is refused by CoreAudio.

import CoreAudio
import Foundation

let SYS = AudioObjectID(kAudioObjectSystemObject)

func addr(_ sel: AudioObjectPropertySelector,
          _ scope: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal)
          -> AudioObjectPropertyAddress {
  AudioObjectPropertyAddress(mSelector: sel, mScope: scope,
                             mElement: kAudioObjectPropertyElementMain)
}

func allDevices() -> [AudioDeviceID] {
  var a = addr(kAudioHardwarePropertyDevices)
  var size: UInt32 = 0
  guard AudioObjectGetPropertyDataSize(SYS, &a, 0, nil, &size) == noErr, size > 0 else { return [] }
  var ids = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
  guard AudioObjectGetPropertyData(SYS, &a, 0, nil, &size, &ids) == noErr else { return [] }
  return ids
}

func stringProp(_ id: AudioDeviceID, _ sel: AudioObjectPropertySelector) -> String {
  var a = addr(sel)
  var size = UInt32(MemoryLayout<CFString?>.size)
  var cf: CFString? = nil
  let st = withUnsafeMutablePointer(to: &cf) {
    $0.withMemoryRebound(to: UInt8.self, capacity: Int(size)) {
      AudioObjectGetPropertyData(id, &a, 0, nil, &size, $0)
    }
  }
  guard st == noErr, let s = cf else { return "" }
  return s as String
}

let name = { (id: AudioDeviceID) in stringProp(id, kAudioObjectPropertyName) }
let uid  = { (id: AudioDeviceID) in stringProp(id, kAudioDevicePropertyDeviceUID) }

// A device is an input or an output depending on which scope carries channels.
// Aggregates and multi-output devices show up here exactly like hardware does.
func channelCount(_ id: AudioDeviceID, input: Bool) -> Int {
  var a = addr(kAudioDevicePropertyStreamConfiguration,
               input ? kAudioObjectPropertyScopeInput : kAudioObjectPropertyScopeOutput)
  var size: UInt32 = 0
  guard AudioObjectGetPropertyDataSize(id, &a, 0, nil, &size) == noErr, size > 0 else { return 0 }
  let raw = UnsafeMutableRawPointer.allocate(byteCount: Int(size),
                                             alignment: MemoryLayout<AudioBufferList>.alignment)
  defer { raw.deallocate() }
  guard AudioObjectGetPropertyData(id, &a, 0, nil, &size, raw) == noErr else { return 0 }
  let list = UnsafeMutableAudioBufferListPointer(raw.assumingMemoryBound(to: AudioBufferList.self))
  return list.reduce(0) { $0 + Int($1.mNumberChannels) }
}

func devices(input: Bool) -> [AudioDeviceID] {
  allDevices().filter { channelCount($0, input: input) > 0 }
}

func defaultDevice(input: Bool) -> AudioDeviceID {
  var a = addr(input ? kAudioHardwarePropertyDefaultInputDevice
                     : kAudioHardwarePropertyDefaultOutputDevice)
  var id = AudioDeviceID(0)
  var size = UInt32(MemoryLayout<AudioDeviceID>.size)
  AudioObjectGetPropertyData(SYS, &a, 0, nil, &size, &id)
  return id
}

func setDefault(input: Bool, _ id: AudioDeviceID) -> Bool {
  var a = addr(input ? kAudioHardwarePropertyDefaultInputDevice
                     : kAudioHardwarePropertyDefaultOutputDevice)
  var v = id
  return AudioObjectSetPropertyData(SYS, &a, 0, nil,
                                    UInt32(MemoryLayout<AudioDeviceID>.size), &v) == noErr
}

// UID first — it survives renames and is what the snapshot stores. Then an
// exact name, then a substring, so "blackhole" finds "BlackHole 2ch".
func resolve(_ spec: String, input: Bool) -> AudioDeviceID? {
  let pool = devices(input: input)
  if let d = pool.first(where: { uid($0) == spec }) { return d }
  if let d = pool.first(where: { name($0) == spec }) { return d }
  let needle = spec.lowercased()
  return pool.first { name($0).lowercased().contains(needle) }
}

func die(_ msg: String, _ code: Int32) -> Never {
  FileHandle.standardError.write(("audiodev: " + msg + "\n").data(using: .utf8)!)
  exit(code)
}

let args = Array(CommandLine.arguments.dropFirst())
guard args.count >= 2, ["list", "get", "set"].contains(args[0]),
      ["in", "out"].contains(args[1]) else {
  die("usage: audiodev list|get|set in|out [device]", 1)
}
let isInput = args[1] == "in"

switch args[0] {
case "list":
  for d in devices(input: isInput) { print(uid(d) + "\t" + name(d)) }
case "get":
  let d = defaultDevice(input: isInput)
  guard d != 0 else { die("no default \(args[1])put device", 2) }
  print(uid(d) + "\t" + name(d))
default:
  guard args.count >= 3 else { die("set needs a device", 1) }
  guard let d = resolve(args[2], input: isInput) else { die("no \(args[1])put device matching \"\(args[2])\"", 2) }
  guard setDefault(input: isInput, d) else { die("CoreAudio refused to make \"\(name(d))\" the default", 2) }
  print(uid(d) + "\t" + name(d))
}
