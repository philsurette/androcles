import type { PlaybookManifest } from "../specs/playbookManifest";

export const fairiesDemoManifest: PlaybookManifest = {
  schema_version: 1,
  format_version: "1.0.0",
  package_type: "playbook",
  production: { source: "working" },
  build: {
    buildId: "fairies-demo",
    buildTimestamp: "2026-05-19T20:38:22Z"
  },
  play: {
    id: "fairies",
    title: "The Curious Case of the Cottingley Fairies",
    authors: ["Claire Wittman"]
  },
  reading: {
    type: "solo",
    build_type: "custom"
  },
  sections: [
    { id: "part-0", part_id: 0, block_id: "0.0", title: "PROLOGUE", ordinal: 0 },
    { id: "part-3", part_id: 3, block_id: "3.0", title: "Scene Six", ordinal: 3 }
  ],
  context: [
    {
      id: "P-1",
      part_id: 0,
      block_id: "0.1",
      kind: "description",
      speaker: "_NARRATOR",
      text: "1966.",
      audio: { path: "audio/segments/_NARRATOR/0_1_1.wav", duration_ms: 1600, required: true },
      content_hash: "sha256:demo-p1"
    },
    {
      id: "P-2:b1",
      part_id: 0,
      block_id: "0.2",
      kind: "blocking",
      speaker: "_NARRATOR",
      text: "stage type=proscenium width=36 depth=24 units=ft",
      content_hash: "sha256:demo-blocking-stage",
      targets: ["*"],
      placement: "before"
    },
    {
      id: "P-3:b1",
      part_id: 0,
      block_id: "0.3",
      kind: "blocking",
      speaker: "_NARRATOR",
      text: "@ interview_chair face=CHRISTINE",
      content_hash: "sha256:demo-blocking-p3",
      targets: ["LILLIAN"],
      placement: "before"
    },
    {
      id: "3-1",
      part_id: 3,
      block_id: "3.1",
      kind: "description",
      speaker: "_NARRATOR",
      text: "LILLIAN and CHRISTINE are looking through a box.",
      audio: { path: "audio/segments/_NARRATOR/3_1_1.wav", duration_ms: 2800, required: true },
      content_hash: "sha256:demo-3-1"
    }
  ],
  roles: [
    {
      id: "CHRISTINE",
      display_name: "CHRISTINE",
      reader: null,
      meta: false,
      parts: [0, 3],
      lines: [
        {
          id: "P-2",
          part_id: 0,
          block_id: "0.2",
          role: "CHRISTINE",
          speaker: "CHRISTINE",
          cue: {
            speaker: "_NARRATOR",
            text: "1966.",
            audio: { path: "audio/segments/_NARRATOR/0_1_1.wav", duration_ms: 1600, required: true }
          },
          response: {
            text: "Do you mind if I record?",
            segments: [
              {
                id: "P-2:s1",
                owners: ["CHRISTINE"],
                text: "Do you mind if I record?",
                audio: { path: "audio/segments/CHRISTINE/0_2_1.wav", duration_ms: 2450, required: true },
                segment_id: "0_2_1",
                content_hash: "sha256:demo-p2"
              }
            ]
          },
          directions: [],
          blocking: [],
          previous_roles: [],
          content_hash: "sha256:demo-p2-line"
        }
      ]
    },
    {
      id: "LILLIAN",
      display_name: "LILLIAN",
      reader: null,
      meta: false,
      parts: [0, 3],
      lines: [
        {
          id: "P-3",
          part_id: 0,
          block_id: "0.3",
          role: "LILLIAN",
          speaker: "LILLIAN",
          cue: {
            speaker: "CHRISTINE",
            text: "Do you mind if I record?",
            audio: { path: "audio/segments/CHRISTINE/0_2_1.wav", duration_ms: 2450, required: true }
          },
          response: {
            text: "Please do.",
            segments: [
              {
                id: "P-3:s1",
                owners: ["LILLIAN"],
                text: "Please do.",
                audio: { path: "audio/segments/LILLIAN/0_3_1.wav", duration_ms: 1500, required: true },
                segment_id: "0_3_1",
                content_hash: "sha256:demo-p3"
              }
            ]
          },
          directions: [],
          blocking: [],
          previous_roles: ["CHRISTINE"],
          content_hash: "sha256:demo-p3-line"
        },
        {
          id: "3-2",
          part_id: 3,
          block_id: "3.2",
          role: "LILLIAN",
          speaker: "LILLIAN",
          cue: {
            speaker: "_NARRATOR",
            text: "LILLIAN and CHRISTINE are looking through a box.",
            audio: { path: "audio/segments/_NARRATOR/3_1_1.wav", duration_ms: 2800, required: true }
          },
          response: {
            text: "I have a dozen such drawings, you know. Though this one is my favourite.",
            segments: [
              {
                id: "3-2:s1",
                owners: ["LILLIAN"],
                text: "I have a dozen such drawings, you know. Though this one is my favourite.",
                audio: { path: "audio/segments/LILLIAN/3_2_1.wav", duration_ms: 5850, required: true },
                segment_id: "3_2_1",
                content_hash: "sha256:demo-3-2"
              }
            ]
          },
          directions: [],
          blocking: [
            {
              id: "3-2:b11",
              targets: ["CHRISTINE"],
              text: "leans in to see the drawing",
              placement: "inline",
              segment_id: "3_2_2",
              content_hash: "sha256:demo-3-2-blocking"
            }
          ],
          previous_roles: [],
          content_hash: "sha256:demo-3-2-line"
        }
      ]
    }
  ],
  assets: [
    { path: "audio/segments/_NARRATOR/0_1_1.wav", duration_ms: 1600, required: true },
    { path: "audio/segments/_NARRATOR/3_1_1.wav", duration_ms: 2800, required: true },
    { path: "audio/segments/CHRISTINE/0_2_1.wav", duration_ms: 2450, required: true },
    { path: "audio/segments/LILLIAN/0_3_1.wav", duration_ms: 1500, required: true },
    { path: "audio/segments/LILLIAN/3_2_1.wav", duration_ms: 5850, required: true }
  ]
};
