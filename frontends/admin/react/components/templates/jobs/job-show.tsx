import React, { FC, useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { useAPI } from "../../../hooks";
import { JobInfo } from "../../../api/colony-print";
import { Button, Link, Tag, Title, Text } from "../../atoms";
import { ContentHeader, DetailGrid } from "../../molecules";
import { formatTimestamp } from "../../../utils";

import "./job-show.css";

export const JobShow: FC = () => {
    const api = useAPI();
    const { id } = useParams<{ id: string }>();
    const [job, setJob] = useState<JobInfo | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchJob = useCallback(async () => {
        if (!id) return;
        setLoading(true);
        try {
            const data = await api.getJob(id);
            setJob(data);
        } catch {
            setJob(null);
        } finally {
            setLoading(false);
        }
    }, [api, id]);

    useEffect(() => {
        fetchJob();
    }, [fetchJob]);

    const formatBytes = (bytes?: number): string => {
        if (bytes === undefined || bytes === null) return "-";
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024)
            return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const statusVariant = (status: string) => {
        if (status === "finished") return "success";
        if (status === "printing") return "warning";
        return "default";
    };

    const fields = job
        ? [
              { label: "ID", value: job.id },
              { label: "Name", value: job.name || "-" },
              {
                  label: "Node",
                  value: (
                      <Link to={`/nodes/${job.node_id}`}>
                          {job.node_id}
                      </Link>
                  )
              },
              {
                  label: "Status",
                  value: (
                      <Tag
                          variant={
                              statusVariant(job.status) as
                                  | "success"
                                  | "warning"
                                  | "default"
                          }
                      >
                          {job.status}
                      </Tag>
                  )
              },
              { label: "Type", value: job.type || "-" },
              { label: "Format", value: job.format || "-" },
              {
                  label: "Data Length",
                  value: formatBytes(job.data_length)
              },
              {
                  label: "Queued",
                  value: formatTimestamp(job.queued_time)
              },
              {
                  label: "Printing Started",
                  value: formatTimestamp(job.printing_time)
              },
              {
                  label: "Finished",
                  value: formatTimestamp(job.finish_time)
              }
          ]
        : [];

    const optionEntries = job?.options
        ? Object.entries(job.options).filter(
              ([, v]) => v !== undefined && v !== null
          )
        : [];

    const outputData = job?.result?.output_data as string | undefined;
    const outputMimeType = (job?.result?.output_mime_type as string | undefined) ?? "application/octet-stream";
    const outputEncoding = (job?.result?.output_encoding as string | undefined) ?? "base64";

    const resultEntries = job?.result
        ? [
              ...Object.entries(job.result).filter(
                  ([key, v]) =>
                      v !== undefined &&
                      v !== null &&
                      key !== "output_data" &&
                      key !== "output_encoding" &&
                      key !== "output_mime_type"
              ),
              ...(outputData
                  ? [
                        ["output_mime_type", outputMimeType],
                        ["output_encoding", outputEncoding],
                        ["output_data", outputData.substring(0, 32) + "..."]
                    ]
                  : [])
          ]
        : [];

    return (
        <div className="job-show">
            <ContentHeader
                title={job?.name || "Job"}
                description={
                    id ? `Job ${id.substring(0, 8)}` : undefined
                }
                actions={
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => window.history.back()}
                    >
                        Back to Jobs
                    </Button>
                }
            />
            <DetailGrid fields={fields} loading={loading} />
            {optionEntries.length > 0 && (
                <div className="job-show-section">
                    <Title level={3}>Options</Title>
                    <DetailGrid
                        fields={optionEntries.map(([key, value]) => ({
                            label: key,
                            value: (
                                <Text>
                                    {typeof value === "object"
                                        ? JSON.stringify(value)
                                        : String(value)}
                                </Text>
                            )
                        }))}
                    />
                </div>
            )}
            {resultEntries.length > 0 && (
                <div className="job-show-section">
                    <Title level={3}>Result</Title>
                    <DetailGrid
                        fields={resultEntries.map(([key, value]) => ({
                            label: key,
                            value: (
                                <Text>
                                    {typeof value === "object"
                                        ? JSON.stringify(value)
                                        : String(value)}
                                </Text>
                            )
                        }))}
                    />
                </div>
            )}
            {outputData && outputEncoding === "base64" && (
                <div className="job-show-section">
                    <Title level={3}>Output</Title>
                    <div className="job-show-output">
                        {outputMimeType === "application/pdf" && (
                            <iframe
                                className="job-show-output-preview"
                                src={`data:${outputMimeType};base64,${outputData}`}
                                title="Output Preview"
                            />
                        )}
                        <a
                            className="job-show-output-download"
                            href={`data:${outputMimeType};base64,${outputData}`}
                            download={`${job?.name || id}.pdf`}
                        >
                            Download
                        </a>
                    </div>
                </div>
            )}
        </div>
    );
};
